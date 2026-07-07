# ChatBot Platform

A multi-tenant chatbot platform. Customers sign up, configure a chatbot for their
website (prompt, source data, display rules, LLM provider), and embed it on **any
site** with a single `<script>` tag. Supports **OpenAI**, **Anthropic** and
**DeepSeek** — each customer brings their own model id and API key.

```
chatBot/
├── backend/   FastAPI + PostgreSQL API (auth, bot config, widget endpoints)
│   └── app/static/widget/chatbot-widget.js   ← the embeddable widget
└── panel/     React (Vite) admin & customer panel
```

## What it does

**Customer flow (in the panel):**
1. Register → log in.
2. Create a chatbot and set:
   - **Website URL** — the main domain.
   - **Display rules** — show on *all pages*, *all pages except* a list, or *only*
     specific URLs/paths (wildcards like `/blog/*` supported).
   - **System prompt** — rules, tone, persona.
   - **Feed data** — the source knowledge the bot answers from (used instead of
     crawling the whole site).
   - **Providers** — enable OpenAI / Anthropic / DeepSeek, type the model id and
     API key for each, and pick the active one.
3. Copy the embed snippet and paste it on the website.

**Roles:** only `admin` and `customer`. Admins can manage all users and view all
bots. New registrations are always `customer`.

**Security:** provider API keys are encrypted at rest (Fernet) and never returned
to the client — only a masked hint (`••••abcd`). Bots are strictly isolated per
owner; admins may access any.

## The embeddable widget

```html
<script src="http://localhost:8000/widget/chatbot-widget.js"
        data-bot-key="YOUR_PUBLIC_KEY" defer></script>
```

The widget (isolated in a Shadow DOM so it never clashes with host-page CSS):
- fetches its public config,
- **checks the page's domain against the bot's configured Website URL** — it only
  renders when the domain matches (or a subdomain of it),
- evaluates the display rules against the current URL and shows/hides itself,
- renders a chat bubble, and talks to `POST /v1/public/bots/{key}/chat`.

**Domain lock.** The bot only appears and works on the domain set in the panel
(`site_url`) and its subdomains. It's enforced twice: the widget won't render on a
mismatched domain, and the chat endpoint rejects browser requests whose `Origin`
doesn't match (returns 403). Leave `site_url` blank to allow any domain (handy for
testing). The panel's own live tester is always allowed.

The backend builds the system prompt from the bot's prompt + feed data, calls the
active provider, stores the conversation, and returns the reply.

---

## Quick start (local dev)

### 1. Database

Using Docker (recommended):
```bash
cd backend
docker compose up -d db     # Postgres on localhost:5432
```
Or point `backend/.env` at any existing PostgreSQL.

### 2. Backend

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/alembic upgrade head          # create tables
./venv/bin/uvicorn app.main:app --reload # http://localhost:8000
```
- API docs: http://localhost:8000/docs
- Default admin (from `.env`): `admin@chatbot.com` / `Admin12345`

> `.env` ships with dev-friendly defaults: `REQUIRE_EMAIL_VERIFICATION=false`
> (so you can log in right after registering with no mail server) and
> `CORS_ORIGINS=*` (so the widget can embed anywhere). **Change the
> `JWT_SECRET_KEY`, `ENCRYPTION_KEY` and admin password before production.**

### 3. Panel

```bash
cd panel
npm install
npm run dev        # http://localhost:5173
```
`panel/.env` sets `VITE_API_BASE=http://localhost:8000`.

### 4. Try the widget

Open `http://localhost:8000/widget/demo.html`, or paste the embed snippet from a
bot's **Embed & Test** tab into any HTML page. The **Embed & Test** tab also has a
live tester that sends a real message through your configured provider.

---

## Run the whole backend with Docker

```bash
cd backend
docker compose up --build      # db + app, runs migrations, serves on :8000
```

## Tests / verification

A standalone smoke test exercises the full API against sqlite with a mocked LLM
(no real API keys needed):

```bash
cd backend
./venv/bin/python smoke_test.py
```

## Provider notes

| Provider  | Endpoint (server-side)                    | Example model     |
|-----------|-------------------------------------------|-------------------|
| OpenAI    | `api.openai.com/v1/chat/completions`      | `gpt-4o-mini`     |
| DeepSeek  | `api.deepseek.com/chat/completions`       | `deepseek-chat`   |
| Anthropic | `api.anthropic.com/v1/messages`           | `claude-sonnet-5` |

The customer's typed model string is used verbatim. Feed data is capped at
`FEED_DATA_MAX_CHARS` (default 20000) and the last `CHAT_HISTORY_LIMIT` (20)
messages are sent as context.
