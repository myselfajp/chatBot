"""Build feed data from a website's sitemap.

Reads a sitemap (or sitemap index), fetches each page, and asks the bot's
configured LLM to extract FAQ question/answer pairs from the page content.
Each generated item records the source page URL. Runs as a background job so
the panel can poll progress.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from typing import List, Tuple

import httpx

from app.core.crypto import decrypt
from app.db.session import SessionLocal
from app.model.feed_job import FeedJob
from app.repository.bot import BotRepository
from app.service import llm

_UA = "Mozilla/5.0 (compatible; ChatBotFeedBot/1.0)"
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_PAGE_CHARS = 6000
_QA_PER_PAGE = 5
_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)


def _fetch(url: str) -> str:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": _UA}) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def parse_sitemap(url: str, max_pages: int) -> List[str]:
    """Return up to max_pages page URLs from a sitemap or sitemap index."""
    xml = _fetch(url)
    locs = [html_lib.unescape(m).strip() for m in _LOC_RE.findall(xml)]
    locs = [l for l in locs if l]
    if "<sitemapindex" in xml.lower():
        pages: List[str] = []
        for sub in locs[:10]:
            try:
                sub_xml = _fetch(sub)
            except Exception:
                continue
            for m in _LOC_RE.findall(sub_xml):
                u = html_lib.unescape(m).strip()
                if u:
                    pages.append(u)
            if len(pages) >= max_pages:
                break
        return pages[:max_pages]
    return locs[:max_pages]


def fetch_page_text(url: str) -> str:
    content = _fetch(url)
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
    except Exception:
        stripped = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", content)
        stripped = re.sub(r"(?s)<[^>]+>", " ", stripped)
        text = html_lib.unescape(stripped)
    return re.sub(r"\s+", " ", text).strip()


def _parse_qa(reply: str) -> List[dict]:
    """Extract a JSON array of {question, answer} from an LLM reply."""
    if not reply:
        return []
    txt = reply.strip()
    # strip code fences
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```$", "", txt).strip()
    start, end = txt.find("["), txt.rfind("]")
    if start != -1 and end != -1 and end > start:
        txt = txt[start : end + 1]
    try:
        data = json.loads(txt)
    except (ValueError, TypeError):
        return []
    out = []
    if isinstance(data, list):
        for d in data:
            if isinstance(d, dict):
                q = (d.get("question") or d.get("q") or "").strip()
                a = (d.get("answer") or d.get("a") or "").strip()
                if q and a:
                    out.append({"question": q, "answer": a})
    return out


def _generate_qa(provider, model, api_key, url, content) -> List[dict]:
    system = (
        "You extract concise FAQ pairs from web page content for a customer-support "
        "chatbot. Reply with ONLY a JSON array, no prose."
    )
    user = (
        f"Web page: {url}\n\n"
        f"Content:\n{content[:_PAGE_CHARS]}\n\n"
        f"Generate up to {_QA_PER_PAGE} question/answer pairs a visitor might ask that "
        f"are answerable ONLY from the content above. Return a JSON array like "
        f'[{{"question":"...","answer":"..."}}]. JSON only.'
    )
    reply = llm.generate_reply(
        provider=provider,
        model=model,
        api_key=api_key,
        system_prompt=system,
        messages=[{"role": "user", "content": user}],
    )
    return _parse_qa(reply)


def process_feed_job(job_id: str, max_pages: int) -> None:
    """Background worker: crawl the sitemap and append generated feed items."""
    db = SessionLocal()
    bot_repo = BotRepository()
    job = None
    try:
        job = db.get(FeedJob, job_id)
        if not job:
            return
        job.status = "running"
        db.commit()

        bot = bot_repo.get_with_providers(db, job.bot_id)
        if not bot:
            job.status = "error"
            job.message = "Bot not found."
            db.commit()
            return

        pconf = next((p for p in bot.providers if p.provider == bot.active_provider), None)
        api_key = decrypt(pconf.api_key_encrypted) if pconf else ""
        if not pconf or not pconf.enabled or not api_key:
            job.status = "error"
            job.message = "The active provider is not configured (enable it and add an API key first)."
            db.commit()
            return

        try:
            urls = parse_sitemap(job.sitemap_url, max_pages)
        except Exception as exc:
            job.status = "error"
            job.message = f"Could not read sitemap: {exc}"
            db.commit()
            return

        if not urls:
            job.status = "error"
            job.message = "No page URLs found in the sitemap."
            db.commit()
            return

        job.pages_total = len(urls)
        db.commit()

        generated: List[Tuple[str, str, str]] = []
        for i, url in enumerate(urls):
            try:
                content = fetch_page_text(url)
                if content:
                    for qa in _generate_qa(
                        bot.active_provider, pconf.model, api_key, url, content
                    ):
                        generated.append((qa["question"], qa["answer"], url))
            except Exception:
                pass  # skip a failing page, keep going
            job.pages_done = i + 1
            db.commit()

        if generated:
            lines = ["", "=== Auto-generated from sitemap ==="]
            for q, a, src in generated:
                lines.append(f"Q: {q}\nA: {a}\n(Source: {src})\n")
            block = "\n".join(lines)
            bot.feed_data = ((bot.feed_data or "") + "\n" + block).strip()

        job.items_added = len(generated)
        job.status = "done"
        job.message = f"Read {job.pages_done} page(s); added {len(generated)} feed item(s)."
        db.commit()
    except Exception as exc:  # noqa: BLE001
        if job is not None:
            try:
                job.status = "error"
                job.message = str(exc)[:500]
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()
