import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.router.auth import router as auth_router
from app.router.user import router as user_router
from app.router.me import router as me_router
from app.router.bot import router as bot_router
from app.router.admin_bot import router as admin_bot_router
from app.router.public import router as public_router
from app.router.upload import router as upload_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # Initialize the database
    init_db()
    yield
    print("Shutting down...")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Rate Limiting Configuration
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore


logger = logging.getLogger("app")


# Global Exception Handler — log details server-side, return a generic message
# so internal error strings are never disclosed to clients.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled error processing %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "Internal server error"},
    )


# CORS Configuration
_cors_origins = (
    ["*"]
    if settings.CORS_ORIGINS.strip() == "*"
    else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(me_router)
app.include_router(bot_router)
app.include_router(admin_bot_router)
app.include_router(public_router)
app.include_router(upload_router)

# Serve the embeddable widget (chatbot-widget.js) and a demo page.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static", "widget")
os.makedirs(_STATIC_DIR, exist_ok=True)
app.mount("/widget", StaticFiles(directory=_STATIC_DIR), name="widget")

# Serve uploaded logos / launcher icons.
_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_UPLOAD_DIR), name="uploads")


@app.get("/v1/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ---- Serve the built React panel (single-port deployment) ----
# Present only when the panel has been built into app/static/panel. In local
# dev the panel runs separately (Vite), so this block is skipped and the API
# behaves as before. Registered last so it never shadows /v1, /widget, /uploads.
_PANEL_DIR = os.path.join(os.path.dirname(__file__), "static", "panel")
if os.path.isfile(os.path.join(_PANEL_DIR, "index.html")):
    _panel_assets = os.path.join(_PANEL_DIR, "assets")
    if os.path.isdir(_panel_assets):
        app.mount(
            "/assets", StaticFiles(directory=_panel_assets), name="panel-assets"
        )

    _panel_index = os.path.join(_PANEL_DIR, "index.html")

    @app.get("/", include_in_schema=False)
    def _spa_root():
        return FileResponse(_panel_index)

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_catchall(full_path: str):
        # Serve a real static file if it exists (favicon, etc.), else the SPA shell.
        candidate = os.path.normpath(os.path.join(_PANEL_DIR, full_path))
        if candidate.startswith(_PANEL_DIR) and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(_panel_index)
