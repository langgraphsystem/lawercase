from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from telegram import Update
from telegram.error import RetryAfter, TelegramError

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
from telegram_interface.bot import (build_application, initialize_application,
                                    set_webhook, shutdown_application)

logger = structlog.get_logger(__name__)

_DEFAULT_WEBHOOK_LOCK_FILENAME = "telegram_webhook.lock"
_DEFAULT_WEBHOOK_LOCK_PATH = Path(tempfile.gettempdir()) / _DEFAULT_WEBHOOK_LOCK_FILENAME
_WEBHOOK_LOCK_PATH = Path(
    os.getenv("TELEGRAM_WEBHOOK_LOCK_FILE") or _DEFAULT_WEBHOOK_LOCK_PATH,
)
_WEBHOOK_LOCK_TIMEOUT = float(os.getenv("TELEGRAM_WEBHOOK_LOCK_TIMEOUT", "15"))
_WEBHOOK_MAX_RETRIES = int(os.getenv("TELEGRAM_WEBHOOK_MAX_RETRIES", "3"))


async def _acquire_webhook_lock(timeout: float) -> bool:
    """Ensure only one worker performs webhook registration."""

    deadline = time.monotonic() + max(timeout, 0)
    while True:
        try:
            _WEBHOOK_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        except Exception:  # pragma: no cover - best effort logging only
            logger.exception(
                "telegram.webhook.lock.mkdir_failed", path=str(_WEBHOOK_LOCK_PATH.parent)
            )
            return False

        try:
            fd = os.open(str(_WEBHOOK_LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                logger.info("telegram.webhook.lock.unavailable", path=str(_WEBHOOK_LOCK_PATH))
                return False
            await asyncio.sleep(0.5)
            continue
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("telegram.webhook.lock.acquire_failed", path=str(_WEBHOOK_LOCK_PATH))
            return False

        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(str(os.getpid()))
        except Exception:  # pragma: no cover
            logger.exception("telegram.webhook.lock.write_failed", path=str(_WEBHOOK_LOCK_PATH))
            os.close(fd)
            try:
                _WEBHOOK_LOCK_PATH.unlink()
            except OSError:
                logger.exception(
                    "telegram.webhook.lock.cleanup_failed", path=str(_WEBHOOK_LOCK_PATH)
                )
                return False
            return False

        logger.debug(
            "telegram.webhook.lock.acquired",
            path=str(_WEBHOOK_LOCK_PATH),
            pid=os.getpid(),
        )
        return True


def _release_webhook_lock() -> None:
    try:
        _WEBHOOK_LOCK_PATH.unlink(missing_ok=True)
        logger.debug("telegram.webhook.lock.released", path=str(_WEBHOOK_LOCK_PATH))
    except FileNotFoundError:  # pragma: no cover - defensive
        pass
    except Exception:  # pragma: no cover - defensive
        logger.exception("telegram.webhook.lock.release_failed", path=str(_WEBHOOK_LOCK_PATH))


async def _inspect_existing_webhook(application, expected_url: str) -> str | None:
    """Log the currently configured webhook URL."""

    try:
        info = await application.bot.get_webhook_info()
    except TelegramError as exc:
        logger.warning(
            "telegram.webhook.info_failed",
            error=str(exc),
        )
        return None

    current_url = info.url or ""
    if current_url == expected_url:
        logger.info("telegram.webhook.already_active", url=expected_url)
    elif not current_url:
        logger.warning("telegram.webhook.not_configured")
    else:
        logger.warning(
            "telegram.webhook.mismatch",
            expected=expected_url,
            current=current_url,
        )
    return current_url or None


async def _ensure_webhook(
    telegram_app,
    *,
    url: str,
    secret_token: str | None,
    drop_pending_updates: bool,
) -> bool:
    """Attempt webhook registration with limited retries on Telegram throttling."""

    attempts = 0
    while attempts < max(_WEBHOOK_MAX_RETRIES, 1):
        attempts += 1
        try:
            await set_webhook(
                telegram_app,
                url=url,
                secret_token=secret_token,
                drop_pending_updates=drop_pending_updates,
            )
            return True
        except RetryAfter as exc:
            wait_seconds = max(int(getattr(exc, "retry_after", 0)), 1)
            logger.warning(
                "telegram.webhook.retry_after",
                url=url,
                attempt=attempts,
                max_attempts=_WEBHOOK_MAX_RETRIES,
                retry_after=wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
        except TelegramError as exc:
            logger.error(
                "telegram.webhook.set_failed",
                url=url,
                attempt=attempts,
                error=str(exc),
            )
            return False
    logger.error(
        "telegram.webhook.set_exhausted",
        url=url,
        attempts=_WEBHOOK_MAX_RETRIES,
    )
    return False


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

    register_builtin_tools()

    telegram_secret = settings.telegram_webhook_secret or None

    # Define Telegram webhook endpoint BEFORE mounting static files
    # This ensures /telegram/webhook is not intercepted by StaticFiles

    @app.on_event("startup")
    async def startup_telegram() -> None:
        telegram_app = build_application(settings=settings)
        await initialize_application(telegram_app)

        webhook_url = _build_webhook_url(settings)
        lock_owned = await _acquire_webhook_lock(_WEBHOOK_LOCK_TIMEOUT)
        set_success = False
        actual_url = webhook_url

        if lock_owned:
            set_success = await _ensure_webhook(
                telegram_app,
                url=webhook_url,
                secret_token=telegram_secret,
                drop_pending_updates=True,
            )
            if not set_success:
                _release_webhook_lock()
                lock_owned = False

        if not set_success:
            inspected_url = await _inspect_existing_webhook(telegram_app, webhook_url)
            if inspected_url:
                actual_url = inspected_url

        app.state.telegram_webhook_lock_owned = bool(set_success and lock_owned)
        app.state.telegram_application = telegram_app
        app.state.telegram_webhook_url = actual_url

        if set_success:
            logger.info("telegram.webhook.active", url=actual_url)
        else:
            logger.info("telegram.webhook.active.reused", url=actual_url)

    @app.on_event("shutdown")
    async def shutdown_telegram() -> None:
        telegram_app = getattr(app.state, "telegram_application", None)
        if telegram_app is None:
            return
        owns_lock = getattr(app.state, "telegram_webhook_lock_owned", False)
        try:
            if owns_lock:
                try:
                    # IMPORTANT: Do NOT delete webhook on shutdown in production
                    # Webhook should persist across restarts/redeploys
                    # Only delete webhook manually when truly needed
                    # await delete_webhook(telegram_app, drop_pending_updates=True)
                    pass
                finally:
                    _release_webhook_lock()
            else:
                logger.debug("telegram.webhook.delete.skipped", reason="not_lock_owner")
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

    # Mount static files LAST to avoid intercepting API routes
    # StaticFiles on "/" will catch all unmatched routes
    static_dir = Path(__file__).parent.parent  # Go up to project root
    if (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
