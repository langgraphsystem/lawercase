from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.routes.health import router as health_router
from api.routes.metrics import router as metrics_router
from api.routes.openapi import router as openapi_router
from api.routes.rag import router as rag_router


def _setup_logging() -> None:
    logger = logging.getLogger("api")
    if not logger.handlers:
        h = logging.StreamHandler()
        fmt = logging.Formatter('%(message)s')
        h.setFormatter(fmt)
        logger.addHandler(h)
    logger.setLevel(logging.INFO)


_setup_logging()
logger = logging.getLogger("api")

app = FastAPI(title="mega_agent_pro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logger(request: Request, call_next: Callable[[Request], Response]):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            {
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": duration_ms,
            }
        )
    return response


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(openapi_router)
app.include_router(rag_router)

