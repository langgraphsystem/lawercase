"""Production-ready FastAPI application.

This module provides:
- Complete API setup with middleware
- Authentication and authorization
- Rate limiting
- Error handling
- Health checks
- OpenAPI documentation
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.middleware_production import (EnhancedRateLimitMiddleware,
                                       ErrorHandlingMiddleware,
                                       PerformanceMiddleware,
                                       RequestIDMiddleware,
                                       SecurityHeadersMiddleware)
from core.config.production_settings import get_settings
from core.logging_utils import get_logger, setup_logging
from core.security import configure_security
from core.security.config import SecurityConfig

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()

    logger.info(
        "Starting MegaAgent Pro API",
        environment=settings.env.value,
        version=settings.app_version,
    )

    # Initialize logging
    setup_logging(
        level=settings.observability.log_level.value,
        log_format=settings.observability.log_format,
        log_file=settings.observability.log_file,
        service_name=settings.observability.tracing_service_name,
    )

    # Security primitives (RBAC, prompt detector)
    configure_security(SecurityConfig())

    # Additional startup tasks
    # - Database connections
    # - Cache connections
    # - Load models
    # - etc.

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down MegaAgent Pro API")

    # Cleanup tasks
    # - Close database connections
    # - Close cache connections
    # - etc.

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    # Create app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Production-ready EB-1A petition analysis and workflow system",
        docs_url=settings.docs_url if not settings.is_production else None,
        redoc_url=settings.redoc_url if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ========================================================================
    # Middleware (order matters - first added = outermost layer)
    # ========================================================================

    # 1. Security headers (outermost)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. CORS
    if settings.security.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.security.cors_origins,
            allow_credentials=settings.security.cors_allow_credentials,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
            allow_headers=["*"],
        )

    # 3. Compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 4. Request ID tracking
    app.add_middleware(RequestIDMiddleware)

    # 5. Performance monitoring
    app.add_middleware(PerformanceMiddleware)

    # 6. Rate limiting
    if settings.features.enable_rate_limiting:
        app.add_middleware(
            EnhancedRateLimitMiddleware,
            requests_per_minute=settings.security.rate_limit_per_minute,
            requests_per_hour=settings.security.rate_limit_per_hour,
        )

    # 7. Error handling (innermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)

    # ========================================================================
    # Exception Handlers
    # ========================================================================

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        from core.exceptions import ValidationError

        error = ValidationError(
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

        logger.warning(
            "Validation error",
            errors=exc.errors(),
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error.to_dict(),
        )

    # ========================================================================
    # Routes
    # ========================================================================

    # Health check endpoints
    from api.routes import health

    app.include_router(health.router, tags=["Health"])

    # Authentication endpoints (if enabled)
    if settings.features.enable_api_auth:
        from api.routes import auth as auth_routes

        app.include_router(auth_routes.router, prefix=f"{settings.api_prefix}/auth", tags=["Auth"])

    # Agent endpoints
    if settings.features.enable_workflow_orchestration:
        from api.routes import agent as agent_routes

        app.include_router(
            agent_routes.router, prefix=f"{settings.api_prefix}/agent", tags=["Agent"]
        )

    # Memory endpoints
    from api.routes import memory as memory_routes

    app.include_router(
        memory_routes.router, prefix=f"{settings.api_prefix}/memory", tags=["Memory"]
    )

    # Evidence analysis endpoints
    if settings.features.enable_evidence_analysis:
        from api.routes import evidence as evidence_routes

        app.include_router(
            evidence_routes.router,
            prefix=f"{settings.api_prefix}/evidence",
            tags=["Evidence"],
        )

    # Workflow endpoints
    if settings.features.enable_workflow_orchestration:
        from api.routes import workflows as workflow_routes

        app.include_router(
            workflow_routes.router,
            prefix=f"{settings.api_prefix}/workflows",
            tags=["Workflows"],
        )

    # RAG endpoints
    if settings.features.enable_rag_pipeline:
        from api.routes import rag as rag_routes

        app.include_router(rag_routes.router, prefix=f"{settings.api_prefix}/rag", tags=["RAG"])

    # Admin endpoints (production only for admins)
    from api.routes import admin as admin_routes

    app.include_router(admin_routes.router, prefix=f"{settings.api_prefix}/admin", tags=["Admin"])

    # Document Monitor endpoints
    from api.routes import document_monitor as document_monitor_routes

    app.include_router(document_monitor_routes.router, tags=["Document Monitor"])

    # Metrics endpoints (Prometheus)
    from api.routes import metrics as metrics_routes

    app.include_router(metrics_routes.router, tags=["Metrics"])

    # ========================================================================
    # Prometheus FastAPI Instrumentation
    # ========================================================================

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        # Initialize instrumentator with custom metrics
        instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/metrics", "/health", "/liveness", "/readiness"],
            env_var_name="ENABLE_METRICS",
            inprogress_name="http_requests_inprogress",
            inprogress_labels=True,
        )

        # Add default metrics (request latency, count, size, etc.)
        instrumentator.add(
            instrumentator.metrics.default(
                should_include_handler=True,
                should_include_method=True,
                should_include_status=True,
                latency_lowr_buckets=(
                    0.01,
                    0.025,
                    0.05,
                    0.075,
                    0.1,
                    0.25,
                    0.5,
                    0.75,
                    1.0,
                    2.5,
                    5.0,
                ),
            )
        )

        # Instrument the app
        instrumentator.instrument(app)

        logger.info("Prometheus FastAPI instrumentation enabled")

    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed, HTTP metrics disabled")

    # ========================================================================
    # Root endpoint
    # ========================================================================

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        """API root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.env.value,
            "status": "operational",
            "docs_url": settings.docs_url,
        }

    # ========================================================================
    # Static Files (serve index.html and other static assets)
    # ========================================================================

    static_dir = Path(__file__).parent.parent  # Go up to project root
    if (static_dir / "index.html").exists():
        # Mount static files at /static to avoid conflicts with API routes
        app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "api.main_production:app",
        host="0.0.0.0",  # nosec B104 - Binding to all interfaces for Docker/K8s
        port=8000,
        reload=settings.is_development,
        log_level=settings.observability.log_level.value.lower(),
        access_log=True,
    )
