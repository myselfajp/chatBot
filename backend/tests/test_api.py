"""End-to-end API tests (sqlite + mocked LLM/network)."""
import uuid

ADMIN = {"email": "admin@chatbot.com", "password": "Admin12345"}


def make_bot(client, headers, with_provider=True):
    """Create a bot and optionally configure a usable provider."""
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


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def test_health(client):
    assert client.get("/v1/health").json()["status"] == "ok"


def test_register_login_customer(client, customer):
    headers, email = customer
    me = client.get("/v1/me", headers=headers).json()
    assert me["email"] == email
    assert me["role"] == "customer"


def test_admin_login(client):
    r = client.post("/v1/auth/login", json=ADMIN)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "admin"


# --------------------------------------------------------------------------- #
# Bot CRUD + config
# --------------------------------------------------------------------------- #
def test_create_and_configure_bot(client, customer):
    headers, _ = customer
    bot = client.post("/v1/bots", json={"name": "Store", "site_url": "https://shop.example.com"}, headers=headers).json()
    assert bot["public_key"]
    assert len(bot["providers"]) == 3
    assert "chatbot-widget.js" in bot["embed_snippet"]

    r = client.put(
        f"/v1/bots/{bot['id']}",
        json={
            "display_mode": "all_except",
            "display_paths": ["/checkout", "/admin/*"],
            "link_buttons": [{"text": "Contact", "slug": "/contact"}],
            "custom_css": ".cbw-msg.bot{color:red;}",
            "custom_js": "root.querySelector('.cbw-name');",
            "launcher_style": "bar",
            "providers": [{"provider": "openai", "enabled": True, "model": "gpt-4o-mini", "api_key": "sk-secret-9999"}],
        },
        headers=headers,
    )
    assert r.status_code == 200
    b = r.json()
    assert b["display_paths"] == ["/checkout", "/admin/*"]
    assert b["link_buttons"] == [{"text": "Contact", "slug": "/contact"}]
    assert b["custom_css"] == ".cbw-msg.bot{color:red;}"
    assert b["launcher_style"] == "bar"
    oai = next(p for p in b["providers"] if p["provider"] == "openai")
    assert oai["enabled"] and oai["has_key"]
    assert "sk-secret-9999" not in r.text  # key never returned
    assert oai["key_hint"].endswith("9999")


def test_invalid_launcher_rejected(client, customer):
    headers, _ = customer
    bot = client.post("/v1/bots", json={"name": "B"}, headers=headers).json()
    r = client.put(f"/v1/bots/{bot['id']}", json={"launcher_style": "nope"}, headers=headers)
    assert r.status_code == 422


def test_ownership_isolation(client):
    # user A creates a bot; user B cannot access it
    a = f"a{uuid.uuid4().hex[:8]}@example.com"
    b = f"b{uuid.uuid4().hex[:8]}@example.com"
    for em in (a, b):
        client.post("/v1/auth/register", json={"email": em, "password": "Password123", "full_name": "x", "phone_number": "09120000000"})
    ha = {"Authorization": "Bearer " + client.post("/v1/auth/login", json={"email": a, "password": "Password123"}).json()["access_token"]}
    hb = {"Authorization": "Bearer " + client.post("/v1/auth/login", json={"email": b, "password": "Password123"}).json()["access_token"]}
    bot = client.post("/v1/bots", json={"name": "A"}, headers=ha).json()
    assert client.get(f"/v1/bots/{bot['id']}", headers=hb).status_code == 403


# --------------------------------------------------------------------------- #
# Public config + chat
# --------------------------------------------------------------------------- #
def test_public_config_hides_secrets(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    cfg = client.get(f"/v1/public/bots/{bot['public_key']}/config").json()
    assert "system_prompt" not in cfg
    assert "providers" not in cfg
    assert "custom_css" in cfg and "link_buttons" in cfg


def test_chat_non_streaming(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/public/bots/{bot['public_key']}/chat", json={"session_id": "s1", "message": "hi"})
    assert r.status_code == 200
    assert "MOCK" in r.json()["reply"]


def test_chat_unconfigured_provider(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers, with_provider=False)
    r = client.post(f"/v1/public/bots/{bot['public_key']}/chat", json={"session_id": "s1", "message": "hi"})
    assert r.status_code == 400


def test_chat_streaming(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/public/bots/{bot['public_key']}/chat/stream", json={"session_id": "st", "message": "hi"})
    assert r.status_code == 200
    # SSE body contains the streamed tokens and a done event
    assert "Hello" in r.text and "world" in r.text
    assert '"done"' in r.text


def test_domain_lock(client, customer):
    headers, _ = customer
    bot = client.post("/v1/bots", json={"name": "D", "site_url": "https://shop.example.com"}, headers=headers).json()
    client.put(
        f"/v1/bots/{bot['id']}",
        json={"active_provider": "openai", "providers": [{"provider": "openai", "enabled": True, "model": "m", "api_key": "k"}]},
        headers=headers,
    )
    pk = bot["public_key"]
    ok = client.post(f"/v1/public/bots/{pk}/chat", json={"session_id": "d", "message": "hi"}, headers={"Origin": "https://shop.example.com"})
    bad = client.post(f"/v1/public/bots/{pk}/chat", json={"session_id": "d", "message": "hi"}, headers={"Origin": "https://evil.com"})
    assert ok.status_code == 200
    assert bad.status_code == 403


# --------------------------------------------------------------------------- #
# History + conversations
# --------------------------------------------------------------------------- #
def test_history_and_conversations(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    pk = bot["public_key"]
    client.post(f"/v1/public/bots/{pk}/chat", json={"session_id": "sess-A", "message": "first"})
    client.post(f"/v1/public/bots/{pk}/chat", json={"session_id": "sess-A", "message": "second"})
    # a different session (like a "new chat")
    client.post(f"/v1/public/bots/{pk}/chat", json={"session_id": "sess-B", "message": "other"})

    hist = client.get(f"/v1/public/bots/{pk}/history", params={"session_id": "sess-A"}).json()
    assert len(hist["messages"]) == 4  # 2 user + 2 assistant

    convos = client.get(f"/v1/bots/{bot['id']}/conversations", headers=headers).json()
    assert convos["total"] == 2  # both sessions kept
    cid = convos["data"][0]["id"]
    detail = client.get(f"/v1/bots/{bot['id']}/conversations/{cid}", headers=headers).json()
    assert len(detail["messages"]) >= 2


# --------------------------------------------------------------------------- #
# Sitemap feed job (Celery eager) + exclude + cancel
# --------------------------------------------------------------------------- #
def test_sitemap_feed_job(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/bots/{bot['id']}/feed/sitemap", json={"sitemap_url": "https://ex.com/sitemap.xml", "max_pages": 5}, headers=headers)
    assert r.status_code == 202
    jid = r.json()["id"]
    job = client.get(f"/v1/bots/{bot['id']}/feed/jobs/{jid}", headers=headers).json()
    assert job["status"] == "done"
    assert job["items_added"] > 0
    updated = client.get(f"/v1/bots/{bot['id']}", headers=headers).json()
    assert "(Source:" in updated["feed_data"]


def test_sitemap_exclude(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/bots/{bot['id']}/feed/sitemap", json={"sitemap_url": "https://ex.com/sitemap.xml", "max_pages": 5, "exclude": ["/a"]}, headers=headers)
    jid = r.json()["id"]
    job = client.get(f"/v1/bots/{bot['id']}/feed/jobs/{jid}", headers=headers).json()
    assert job["pages_total"] == 1  # /a excluded, only /b remains


def test_sitemap_cancel_control(client, customer):
    """A pre-set cancel flag makes the task discard everything."""
    headers, _ = customer
    bot = make_bot(client, headers)
    from app.db.session import SessionLocal
    from app.model.feed_job import FeedJob
    from app.service.sitemap import process_feed_job

    db = SessionLocal()
    job = FeedJob(bot_id=bot["id"], sitemap_url="https://ex.com/sitemap.xml", status="queued", control="cancel")
    db.add(job)
    db.commit()
    job_id = job.id
    db.close()

    process_feed_job.apply(args=[job_id, 5, None])  # run eagerly

    j = client.get(f"/v1/bots/{bot['id']}/feed/jobs/{job_id}", headers=headers).json()
    assert j["status"] == "cancelled"
    assert j["items_added"] == 0


def test_feed_stop_cancel_endpoints(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/bots/{bot['id']}/feed/sitemap", json={"sitemap_url": "https://ex.com/sitemap.xml"}, headers=headers)
    jid = r.json()["id"]
    # job already finished in eager mode -> control endpoints are a no-op but must not error
    assert client.post(f"/v1/bots/{bot['id']}/feed/jobs/{jid}/stop", headers=headers).status_code == 200
    assert client.post(f"/v1/bots/{bot['id']}/feed/jobs/{jid}/cancel", headers=headers).status_code == 200


# --------------------------------------------------------------------------- #
# Style assistant + upload + admin
# --------------------------------------------------------------------------- #
def test_style_assistant(client, customer):
    headers, _ = customer
    bot = make_bot(client, headers)
    r = client.post(f"/v1/bots/{bot['id']}/style-assistant", json={"messages": [{"role": "user", "content": "make it blue"}]}, headers=headers)
    assert r.status_code == 200
    assert r.json()["reply"]


def test_upload(client, customer):
    import base64
    headers, _ = customer
    bot = client.post("/v1/bots", json={"name": "U"}, headers=headers).json()
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    ok = client.post(f"/v1/bots/{bot['id']}/upload", files={"file": ("l.png", png, "image/png")}, headers=headers)
    assert ok.status_code == 200 and "/uploads/" in ok.json()["url"]
    bad = client.post(f"/v1/bots/{bot['id']}/upload", files={"file": ("x.txt", b"hi", "text/plain")}, headers=headers)
    assert bad.status_code == 400


def test_admin_endpoints(client, customer):
    headers, _ = customer  # a customer exists + a bot
    make_bot(client, headers)
    ha = {"Authorization": "Bearer " + client.post("/v1/auth/login", json=ADMIN).json()["access_token"]}
    assert client.get("/v1/admin/users", headers=ha).status_code == 200
    assert client.get("/v1/admin/bots", headers=ha).status_code == 200
    # customer cannot access admin
    assert client.get("/v1/admin/bots", headers=headers).status_code == 403
