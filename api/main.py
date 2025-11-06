from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from telegram import Update

from api.middleware import (RateLimitMiddleware, RequestMetricsMiddleware,
                            get_rate_limit_settings)
from api.routes import agent as agent_routes
from api.routes import cases as cases_routes
from api.routes import document_monitor as document_monitor_routes
from api.routes import health as health_routes
from api.routes import memory as memory_routes
from api.routes import metrics as metrics_routes
from api.routes import workflows as workflows_routes
from api.startup import register_builtin_tools
from config.settings import AppSettings, get_settings
from core.observability import (TracingConfig, init_logging_from_env,
                                init_tracing)
from core.security import configure_security
from core.security.config import SecurityConfig
from telegram_interface.bot import (build_application, delete_webhook,
                                    initialize_application, set_webhook,
                                    shutdown_application)

logger = structlog.get_logger(__name__)


def _build_webhook_url(settings: AppSettings) -> str:
    """Build the public webhook URL for Telegram.

    Checks in order:
    1. PUBLIC_BASE_URL (explicitly set)
    2. RAILWAY_STATIC_URL (Railway's public URL)
    3. RAILWAY_PUBLIC_DOMAIN (Railway custom domain)
    """
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
    elif settings.railway_static_url:
        # Railway provides RAILWAY_STATIC_URL with full https:// URL
        base = settings.railway_static_url.rstrip("/")
    elif settings.railway_public_domain:
        domain = settings.railway_public_domain.strip()
        if domain.startswith(("http://", "https://")):
            base = domain.rstrip("/")
        else:
            base = f"https://{domain}".rstrip("/")
    else:
        raise RuntimeError(
            "Unable to derive public webhook URL. "
            "Set PUBLIC_BASE_URL, or ensure Railway service has a public domain. "
            "Available Railway vars: RAILWAY_STATIC_URL or RAILWAY_PUBLIC_DOMAIN."
        )

    webhook_url = f"{base}/telegram/webhook"
    logger.info(
        "webhook.url.derived",
        url=webhook_url,
        source=(
            "PUBLIC_BASE_URL"
            if settings.public_base_url
            else "RAILWAY_STATIC_URL" if settings.railway_static_url else "RAILWAY_PUBLIC_DOMAIN"
        ),
    )
    return webhook_url


def create_app() -> FastAPI:
    app = FastAPI(title="mega_agent_pro API", version="1.0")

    # Observability setup
    init_logging_from_env()
    init_tracing(TracingConfig.from_env())

    # CORS from security config
    sc = SecurityConfig()
    configure_security(sc)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sc.cors_allowed_origins,
        allow_credentials=sc.cors_allow_credentials,
        allow_methods=sc.cors_allowed_methods,
        allow_headers=sc.cors_allowed_headers,
    )

    limit, window = get_rate_limit_settings()
    app.add_middleware(RateLimitMiddleware, limit=limit, window=window)
    app.add_middleware(RequestMetricsMiddleware)

    settings = get_settings()

    # Routes
    app.include_router(health_routes.router)
    app.include_router(agent_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(cases_routes.router)
    app.include_router(metrics_routes.router)
    app.include_router(workflows_routes.router)
    app.include_router(document_monitor_routes.router)

    # Serve index.html from root directory
    static_dir = Path(__file__).parent.parent  # Go up to project root
    if (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    register_builtin_tools()

    telegram_secret = settings.telegram_webhook_secret or None

    @app.on_event("startup")
    async def startup_telegram() -> None:
        telegram_app = build_application(settings=settings)
        await initialize_application(telegram_app)

        webhook_url = _build_webhook_url(settings)
        await set_webhook(
            telegram_app,
            url=webhook_url,
            secret_token=telegram_secret,
            drop_pending_updates=True,
        )

        app.state.telegram_application = telegram_app
        app.state.telegram_webhook_url = webhook_url
        logger.info("telegram.webhook.active", url=webhook_url)

    @app.on_event("shutdown")
    async def shutdown_telegram() -> None:
        telegram_app = getattr(app.state, "telegram_application", None)
        if telegram_app is None:
            return
        try:
            await delete_webhook(telegram_app, drop_pending_updates=True)
        finally:
            await shutdown_application(telegram_app)
            logger.info("telegram.webhook.stopped")

    @app.post("/telegram/webhook")
    async def telegram_webhook(request: Request) -> dict[str, str]:
        telegram_app = getattr(request.app.state, "telegram_application", None)
        if telegram_app is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Telegram bot not initialized")

        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if telegram_secret and header_secret != telegram_secret:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid secret token")

        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)

        return {"status": "ok"}

    return app


app = create_app()
