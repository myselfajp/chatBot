"""LLM provider abstraction.

Supports OpenAI, DeepSeek (OpenAI-compatible) and Anthropic. Each bot stores a
free-form model string and an API key per provider; this module dispatches a
chat completion to the selected provider and returns the assistant's reply text.
"""
import json
from typing import Dict, Iterator, List

import httpx
from fastapi import HTTPException, status

SUPPORTED_PROVIDERS = ("openai", "anthropic", "deepseek")

# Reasonable defaults; the customer's typed model string always wins.
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-5",
    "deepseek": "deepseek-chat",
}

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_MAX_TOKENS = 1024


def generate_reply(
    provider: str,
    model: str,
    api_key: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
) -> str:
    """Send a chat request to ``provider`` and return the assistant reply text.

    ``messages`` is a list of {"role": "user"|"assistant", "content": str}.
    Raises HTTPException(502) on provider/network errors.
    """
    provider = (provider or "").lower()
    model = (model or "").strip() or DEFAULT_MODELS.get(provider, "")

    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}",
        )
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key configured for provider '{provider}'.",
        )

    try:
        if provider == "anthropic":
            return _anthropic(model, api_key, system_prompt, messages)
        # openai and deepseek share the OpenAI chat-completions shape
        base_url = (
            "https://api.deepseek.com"
            if provider == "deepseek"
            else "https://api.openai.com/v1"
        )
        return _openai_compatible(base_url, model, api_key, system_prompt, messages)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        detail = _extract_error(exc.response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider} API error: {detail}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach {provider} API: {exc}",
        ) from exc


def _openai_compatible(
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
) -> str:
    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(messages)

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": payload_messages,
                "max_tokens": _MAX_TOKENS,
            },
        )
        resp.raise_for_status()

    try:
        data = resp.json()  # may raise ValueError on a non-JSON 2xx body
        content = data["choices"][0]["message"].get("content")
        return (content or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from provider.",
        ) from exc


def _anthropic(
    model: str,
    api_key: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
) -> str:
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": _MAX_TOKENS,
                "system": system_prompt or "",
                "messages": messages,
            },
        )
        resp.raise_for_status()

    try:
        data = resp.json()  # may raise ValueError on a non-JSON 2xx body
        # content is a list of blocks; concatenate text blocks.
        parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        text = "".join(parts).strip()
        if not text:
            raise ValueError("empty content")
        return text
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from Anthropic.",
        ) from exc


_STREAM_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def generate_reply_stream(
    provider: str,
    model: str,
    api_key: str,
    system_prompt: str,
    messages: List[Dict[str, str]],
) -> Iterator[str]:
    """Yield the assistant reply as text chunks (streaming)."""
    provider = (provider or "").lower()
    model = (model or "").strip() or DEFAULT_MODELS.get(provider, "")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not api_key:
        raise HTTPException(status_code=400, detail=f"No API key configured for '{provider}'.")

    if provider == "anthropic":
        yield from _anthropic_stream(model, api_key, system_prompt, messages)
    else:
        base_url = (
            "https://api.deepseek.com" if provider == "deepseek" else "https://api.openai.com/v1"
        )
        yield from _openai_stream(base_url, provider, model, api_key, system_prompt, messages)


def _openai_stream(base_url, provider, model, api_key, system_prompt, messages):
    payload_messages = []
    if system_prompt:
        payload_messages.append({"role": "system", "content": system_prompt})
    payload_messages.extend(messages)
    with httpx.Client(timeout=_STREAM_TIMEOUT) as client:
        with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": payload_messages,
                "max_tokens": _MAX_TOKENS,
                "stream": True,
            },
        ) as resp:
            if resp.status_code >= 400:
                resp.read()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"{provider} API error: {_extract_error(resp)}",
                )
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    chunk = data["choices"][0]["delta"].get("content")
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                if chunk:
                    yield chunk


def _anthropic_stream(model, api_key, system_prompt, messages):
    with httpx.Client(timeout=_STREAM_TIMEOUT) as client:
        with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": _MAX_TOKENS,
                "system": system_prompt or "",
                "messages": messages,
                "stream": True,
            },
        ) as resp:
            if resp.status_code >= 400:
                resp.read()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"anthropic API error: {_extract_error(resp)}",
                )
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield delta["text"]


def _extract_error(response: httpx.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict) and err.get("message"):
                return str(err["message"])
            if isinstance(err, str):
                return err
            if data.get("message"):
                return str(data["message"])
        return response.text[:300]
    except Exception:
        return f"HTTP {response.status_code}"
