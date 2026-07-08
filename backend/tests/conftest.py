"""Pytest fixtures: sqlite DB, eager Celery, mocked LLM + network, TestClient."""
import os

# Configure the environment BEFORE importing the app.
os.environ["DATABASE_URL"] = "sqlite:///./test_pytest.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

import pytest  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

# Register every model so create_all builds the full schema.
import app.model.user  # noqa: E402,F401
import app.model.login_otp  # noqa: E402,F401
import app.model.email_verification_token  # noqa: E402,F401
import app.model.password_reset_token  # noqa: E402,F401
import app.model.bot  # noqa: E402,F401
import app.model.bot_provider  # noqa: E402,F401
import app.model.conversation  # noqa: E402,F401
import app.model.message  # noqa: E402,F401
import app.model.feed_job  # noqa: E402,F401

from app.service import llm as llm_module  # noqa: E402
from app.service import sitemap as sitemap_module  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    if os.path.exists("test_pytest.db"):
        os.remove("test_pytest.db")
    Base.metadata.create_all(engine)
    yield
    if os.path.exists("test_pytest.db"):
        os.remove("test_pytest.db")


@pytest.fixture(autouse=True)
def _mock_external(monkeypatch):
    """Mock the LLM and network so tests need no real keys or internet."""

    def fake_reply(provider, model, api_key, system_prompt, messages):
        last = messages[-1]["content"] if messages else ""
        if "JSON array" in last or "question/answer" in last:
            return '[{"question":"What is X?","answer":"X is a test."}]'
        return f"MOCK[{provider}]: {last}"

    def fake_stream(provider, model, api_key, system_prompt, messages):
        for tok in ["Hello", ", ", "world", "!"]:
            yield tok

    def fake_fetch(url):
        if "sitemap" in url:
            return (
                '<?xml version="1.0"?><urlset>'
                "<url><loc>https://ex.com/a</loc></url>"
                "<url><loc>https://ex.com/b</loc></url>"
                "</urlset>"
            )
        return "<html><body><h1>T</h1><p>Content about products.</p></body></html>"

    monkeypatch.setattr(llm_module, "generate_reply", fake_reply)
    monkeypatch.setattr(llm_module, "generate_reply_stream", fake_stream)
    monkeypatch.setattr(sitemap_module, "_fetch", fake_fetch)


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Tests all share one client IP, so disable slowapi rate limiting."""
    import app.main as main_mod
    from app.router import auth as auth_mod
    from app.router import public as public_mod

    for mod in (main_mod, auth_mod, public_mod):
        if hasattr(mod, "limiter"):
            mod.limiter.enabled = False
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


_COUNTER = {"n": 0}


@pytest.fixture
def customer(client):
    """Register + log in a fresh customer; return (headers, email)."""
    _COUNTER["n"] += 1
    email = f"cust{_COUNTER['n']}@example.com"
    password = "Password123"
    client.post(
        "/v1/auth/register",
        json={"email": email, "password": password, "full_name": "T", "phone_number": "09120000000"},
    )
    r = client.post("/v1/auth/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


def make_bot(client, headers, with_provider=True):
    """Create a bot and (optionally) configure a usable provider."""
    bot = client.post("/v1/bots", json={"name": "B", "site_url": ""}, headers=headers).json()
    if with_provider:
        client.put(
            f"/v1/bots/{bot['id']}",
            json={
                "active_provider": "openai",
                "providers": [
                    {"provider": "openai", "enabled": True, "model": "gpt-4o-mini", "api_key": "sk-test-123"}
                ],
            },
            headers=headers,
        )
        bot = client.get(f"/v1/bots/{bot['id']}", headers=headers).json()
    return bot
