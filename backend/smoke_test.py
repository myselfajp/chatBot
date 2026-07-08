"""Standalone smoke test: exercises the full API against an in-memory-ish
sqlite DB, mocking the LLM provider so no real API keys are needed.

Run from the backend dir with the venv:
    ./venv/bin/python smoke_test.py
"""
import os
import sys

# Use sqlite so no Postgres is required (overrides .env DATABASE_URL).
os.environ["DATABASE_URL"] = "sqlite:///./smoke_test.db"
# Make sure a fresh DB each run.
if os.path.exists("smoke_test.db"):
    os.remove("smoke_test.db")

# Register all models, then create the schema.
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
import app.model.user  # noqa: E402,F401
import app.model.login_otp  # noqa: E402,F401
import app.model.email_verification_token  # noqa: E402,F401
import app.model.password_reset_token  # noqa: E402,F401
import app.model.bot  # noqa: E402,F401
import app.model.bot_provider  # noqa: E402,F401
import app.model.conversation  # noqa: E402,F401
import app.model.message  # noqa: E402,F401
import app.model.feed_job  # noqa: E402,F401

Base.metadata.create_all(engine)

# Mock the LLM call.
from app.service import llm  # noqa: E402

def _fake_reply(provider, model, api_key, system_prompt, messages):
    last = messages[-1]["content"] if messages else ""
    if "JSON array" in last or "question/answer" in last:
        return '[{"question":"What is X?","answer":"X is a test answer."}]'
    return f"[{provider}:{model}] echo -> {last}"

llm.generate_reply = _fake_reply

# Mock network fetches for the sitemap feed job.
from app.service import sitemap as _sitemap  # noqa: E402

def _fake_fetch(url):
    if "sitemap" in url:
        return (
            '<?xml version="1.0"?><urlset>'
            "<url><loc>https://ex.com/a</loc></url>"
            "<url><loc>https://ex.com/b</loc></url>"
            "</urlset>"
        )
    return "<html><body><h1>Page</h1><p>Content about products and returns.</p></body></html>"

_sitemap._fetch = _fake_fetch

from app import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

FAILS = []

def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)

with TestClient(main.app) as client:
    print("== health ==")
    r = client.get("/v1/health")
    check("health ok", r.status_code == 200 and r.json().get("status") == "ok")

    print("== register customer ==")
    reg = {
        "email": "cust@example.com",
        "password": "Password123",
        "full_name": "Test Customer",
        "phone_number": "09120000000",
    }
    r = client.post("/v1/auth/register", json=reg)
    check("register 201", r.status_code == 201, r.text)

    print("== login customer ==")
    r = client.post("/v1/auth/login", json={"email": reg["email"], "password": reg["password"]})
    check("login 200", r.status_code == 200, r.text)
    data = r.json()
    check("got token", "access_token" in data, r.text)
    check("role is customer", data.get("user", {}).get("role") == "customer", r.text)
    token = data.get("access_token", "")
    H = {"Authorization": f"Bearer {token}"}

    print("== me ==")
    r = client.get("/v1/me", headers=H)
    check("me ok", r.status_code == 200 and r.json().get("email") == reg["email"], r.text)

    print("== create bot ==")
    r = client.post("/v1/bots", json={"name": "My Store Bot", "site_url": "https://shop.example.com"}, headers=H)
    check("create bot 201", r.status_code == 201, r.text)
    bot = r.json()
    bot_id = bot.get("id")
    pub = bot.get("public_key")
    check("has public_key", bool(pub), r.text)
    check("3 providers seeded", len(bot.get("providers", [])) == 3, r.text)
    check("embed snippet present", "chatbot-widget.js" in bot.get("embed_snippet", ""), r.text)

    print("== list bots ==")
    r = client.get("/v1/bots", headers=H)
    check("list bots ok", r.status_code == 200 and r.json().get("total") == 1, r.text)

    print("== update bot (config + provider + key) ==")
    upd = {
        "system_prompt": "You are a friendly store assistant. Be concise.",
        "feed_data": "We sell shoes. Returns accepted within 30 days.",
        "display_mode": "all_except",
        "display_paths": ["/checkout", "/admin/*"],
        "active_provider": "openai",
        "widget_title": "Webster",
        "bot_subtitle": "Product Specialist",
        "logo_url": "https://example.com/logo.png",
        "welcome_message": "Hi! Ask me about our shoes.",
        "quick_replies": ["Contact sales", "I need support"],
        "link_buttons": [
            {"text": "Contact us", "slug": "/contact"},
            {"text": "Docs", "slug": "https://docs.example.com"},
        ],
        "footer_text": "By continuing you agree to our policy.",
        "accent_color": "#ff5722",
        "launcher_style": "bar",
        "providers": [
            {"provider": "openai", "enabled": True, "model": "gpt-4o-mini", "api_key": "sk-secret-123"},
        ],
    }
    r = client.put(f"/v1/bots/{bot_id}", json=upd, headers=H)
    check("update bot ok", r.status_code == 200, r.text)
    b2 = r.json()
    check("paths stored as list", b2.get("display_paths") == ["/checkout", "/admin/*"], r.text)
    check("launcher_style saved", b2.get("launcher_style") == "bar", r.text)
    check("subtitle saved", b2.get("bot_subtitle") == "Product Specialist", r.text)
    lbs = b2.get("link_buttons") or []
    check("link_buttons saved (2)", len(lbs) == 2, r.text)
    check("link_button has text+slug", lbs and lbs[0].get("text") == "Contact us" and lbs[0].get("slug") == "/contact", r.text)
    check("logo_url saved", b2.get("logo_url") == "https://example.com/logo.png", r.text)
    check("quick_replies list", b2.get("quick_replies") == ["Contact sales", "I need support"], r.text)
    check("footer_text saved", b2.get("footer_text") == "By continuing you agree to our policy.", r.text)
    oai = next((p for p in b2["providers"] if p["provider"] == "openai"), {})
    check("openai enabled", oai.get("enabled") is True, r.text)
    check("openai has_key", oai.get("has_key") is True, r.text)
    check("key masked (no raw key)", "sk-secret-123" not in r.text, r.text)
    check("key hint ends 123", oai.get("key_hint", "").endswith("123"), r.text)

    print("== upload asset ==")
    import base64
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    r = client.post(
        f"/v1/bots/{bot_id}/upload",
        files={"file": ("logo.png", png, "image/png")},
        headers=H,
    )
    check("upload ok", r.status_code == 200, r.text)
    check("upload returns url", "/uploads/" in r.json().get("url", ""), r.text)
    r = client.post(
        f"/v1/bots/{bot_id}/upload",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers=H,
    )
    check("upload rejects non-image (400)", r.status_code == 400, r.text)
    r = client.put(f"/v1/bots/{bot_id}", json={"launcher_style": "nope"}, headers=H)
    check("invalid launcher_style rejected (422)", r.status_code == 422, r.text)

    print("== sitemap -> feed job ==")
    r = client.post(
        f"/v1/bots/{bot_id}/feed/sitemap",
        json={"sitemap_url": "https://ex.com/sitemap.xml", "max_pages": 5, "exclude": ["/a"]},
        headers=H,
    )
    check("sitemap job accepted (202)", r.status_code == 202, r.text)
    jid = r.json().get("id", "")
    # TestClient runs the background task before returning, so it should be done.
    r = client.get(f"/v1/bots/{bot_id}/feed/jobs/{jid}", headers=H)
    job = r.json()
    check("job status done", job.get("status") == "done", r.text)
    check("job added items", job.get("items_added", 0) > 0, r.text)
    # sitemap has /a and /b; excluding /a leaves 1 page
    check("exclude skipped a page (1 total)", job.get("pages_total") == 1, r.text)
    r = client.get(f"/v1/bots/{bot_id}", headers=H)
    check("feed has (Source: ...) attribution", "(Source:" in r.json().get("feed_data", ""), r.json().get("feed_data", "")[:120])

    print("== ownership isolation ==")
    # second user cannot access first user's bot
    reg2 = {"email": "other@example.com", "password": "Password123", "full_name": "Other", "phone_number": "09120000001"}
    client.post("/v1/auth/register", json=reg2)
    r = client.post("/v1/auth/login", json={"email": reg2["email"], "password": reg2["password"]})
    H2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get(f"/v1/bots/{bot_id}", headers=H2)
    check("other user blocked (403)", r.status_code == 403, r.text)

    print("== public config ==")
    r = client.get(f"/v1/public/bots/{pub}/config")
    check("public config ok", r.status_code == 200, r.text)
    cfg = r.json()
    check("config has display_mode", cfg.get("display_mode") == "all_except", r.text)
    check("config hides prompt", "system_prompt" not in cfg, r.text)
    check("config has logo_url", cfg.get("logo_url") == "https://example.com/logo.png", r.text)
    check("config has quick_replies", cfg.get("quick_replies") == ["Contact sales", "I need support"], r.text)
    check("config has subtitle", cfg.get("bot_subtitle") == "Product Specialist", r.text)
    check("config has launcher_style", cfg.get("launcher_style") == "bar", r.text)
    check("config has link_buttons", len(cfg.get("link_buttons") or []) == 2, r.text)

    print("== public chat ==")
    r = client.post(f"/v1/public/bots/{pub}/chat", json={"session_id": "sess-1", "message": "Do you accept returns?"})
    check("chat ok", r.status_code == 200, r.text)
    check("got reply", "echo ->" in r.json().get("reply", ""), r.text)
    # second turn keeps session
    r = client.post(f"/v1/public/bots/{pub}/chat", json={"session_id": "sess-1", "message": "thanks"})
    check("chat 2nd turn ok", r.status_code == 200, r.text)

    print("== domain lock (site_url = shop.example.com) ==")
    def chat_from(origin):
        return client.post(
            f"/v1/public/bots/{pub}/chat",
            json={"session_id": "sess-dom", "message": "hi"},
            headers={"Origin": origin} if origin else {},
        )
    check("matching origin ok", chat_from("https://shop.example.com").status_code == 200)
    check("www + exact ok", chat_from("https://www.shop.example.com").status_code == 200)
    r = chat_from("https://evil.com")
    check("mismatched origin blocked (403)", r.status_code == 403, r.text)
    check("panel/front origin ok", chat_from("http://localhost:5173").status_code == 200)
    check("no origin (curl/tester) ok", chat_from(None).status_code == 200)

    print("== chat when unconfigured provider ==")
    # switch active provider to one without a key
    client.put(f"/v1/bots/{bot_id}", json={"active_provider": "anthropic"}, headers=H)
    r = client.post(f"/v1/public/bots/{pub}/chat", json={"session_id": "sess-2", "message": "hi"})
    check("unconfigured -> 400", r.status_code == 400, r.text)

    print("== admin login + admin endpoints ==")
    r = client.post("/v1/auth/login", json={"email": "admin@chatbot.com", "password": "Admin12345"})
    check("admin login ok", r.status_code == 200, r.text)
    HA = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/v1/admin/users", headers=HA)
    check("admin list users ok", r.status_code == 200, r.text)
    r = client.get("/v1/admin/bots", headers=HA)
    check("admin list bots ok", r.status_code == 200 and r.json().get("total") == 1, r.text)
    # customer forbidden on admin
    r = client.get("/v1/admin/bots", headers=H)
    check("customer blocked from admin (403)", r.status_code == 403, r.text)

    print("== delete bot ==")
    r = client.delete(f"/v1/bots/{bot_id}", headers=H)
    check("delete bot 204", r.status_code == 204, r.text)

print()
if FAILS:
    print(f"❌ {len(FAILS)} check(s) failed: {FAILS}")
    sys.exit(1)
print("✅ All smoke checks passed.")
