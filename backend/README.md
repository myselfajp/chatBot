# ChatBot Platform — Backend (FastAPI)

FastAPI + PostgreSQL backend for the ChatBot Platform: authentication, per-customer
chatbot configuration, LLM provider integration, and the public endpoints the
embeddable widget talks to.

Layered architecture: `model → repository → service → router`, with `schema`
(Pydantic), `core` (config, security, jwt, crypto, email, validation) and Alembic
migrations.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env            # then edit secrets
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs.

## Roles

Only `admin` and `customer`. New registrations default to `customer`; the initial
admin is seeded from `ADMIN_EMAIL` / `ADMIN_PASSWORD` on startup.

## Key endpoints

**Auth** (`/v1/auth`): `register`, `login` (JWT, optional email OTP 2FA),
`verify-email`, `forgot-password`, `reset-password`.
**Me** (`/v1/me`): current user (used by the panel on load).

**Bots** (`/v1/bots`, auth required, scoped to the owner):
- `GET /v1/bots` — list my bots
- `POST /v1/bots` — create (seeds the 3 provider rows, disabled)
- `GET /v1/bots/{id}` — full config (owner or admin)
- `PUT /v1/bots/{id}` — update config, prompt, feed data, display rules, providers
- `DELETE /v1/bots/{id}`

**Admin** (`/v1/admin`): `users` CRUD, `GET /v1/admin/bots` (all bots + owner).

**Public** (`/v1/public`, no auth, CORS `*`):
- `GET /bots/{public_key}/config` — non-secret config for the widget
- `POST /bots/{public_key}/chat` — `{ session_id, message } → { reply }` (rate limited)

**Widget:** served statically at `/widget/chatbot-widget.js` (+ `/widget/demo.html`).

## Models

`User`, `Bot`, `BotProvider` (one row per provider per bot; API key Fernet-encrypted),
`Conversation`, `Message`, plus the auth token tables from the base
(`login_otps`, `email_verification_tokens`, `password_reset_tokens`).

## Provider config

Each bot has a `BotProvider` for `openai`, `anthropic`, `deepseek`. A provider is
usable when `enabled=true` and it has an API key. `Bot.active_provider` selects
which one the widget uses. Provider dispatch lives in `app/service/llm.py`
(OpenAI + DeepSeek share the chat-completions shape; Anthropic uses the messages API).

## Security notes

- API keys are encrypted with Fernet (`ENCRYPTION_KEY`) and never returned — only a
  masked hint (`app/core/crypto.py`).
- Bots are isolated per owner; admins bypass ownership checks.
- `POST /v1/public/.../chat` is rate limited (30/min/IP); auth endpoints 5/min/IP.

## Env

See `.env.example`. Notable additions over the base template:
`ENCRYPTION_KEY` (required, Fernet key), `FRONTEND_URL`, `FEED_DATA_MAX_CHARS`,
`CHAT_HISTORY_LIMIT`.

## Smoke test

```bash
./venv/bin/python smoke_test.py   # full API round-trip on sqlite, mocked LLM
```

## Migrations

```bash
./venv/bin/alembic revision --autogenerate -m "message"
./venv/bin/alembic upgrade head
```
