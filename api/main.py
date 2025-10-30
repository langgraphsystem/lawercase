from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.middleware import RateLimitMiddleware, RequestMetricsMiddleware, get_rate_limit_settings
from api.routes import (
    agent as agent_routes,
    cases as cases_routes,
    document_monitor as document_monitor_routes,
    health as health_routes,
    memory as memory_routes,
    metrics as metrics_routes,
    workflows as workflows_routes,
)
from api.startup import register_builtin_tools
from core.observability import TracingConfig, init_logging_from_env, init_tracing
from core.security import configure_security
from core.security.config import SecurityConfig


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

    return app


app = create_app()
