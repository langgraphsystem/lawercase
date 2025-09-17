from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from config.settings import get_settings


def _redact(value: Optional[str]) -> str:
    if not value:
        return ""
    # Redact credentials in URLs like postgres://user:pass@host/db
    try:
        # Very light redaction; avoid importing urlparse
        if "@" in value and "://" in value:
            scheme, rest = value.split("://", 1)
            if "@" in rest and ":" in rest.split("@", 1)[0]:
                creds, host = rest.split("@", 1)
                user = creds.split(":", 1)[0]
                return f"{scheme}://{user}:***@{host}"
    except Exception:
        pass
    return "***"


logger = logging.getLogger("core.db")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


class Database:
    """Async SQLAlchemy engine + session factory."""

    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    def _build_engine(self) -> AsyncEngine:
        settings = get_settings()
        db_url = settings.database_url
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set")

        # Normalize driver: allow postgres:// -> postgresql+psycopg://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        connect_args = {}
        sslmode = settings.db_sslmode or os.getenv("PGSSLMODE")
        if sslmode:
            # psycopg3 accepts sslmode in query or connect args; keep simple via query param
            if "sslmode=" not in db_url:
                sep = "&" if "?" in db_url else "?"
                db_url = f"{db_url}{sep}sslmode={sslmode}"

        logger.info("Initializing DB engine url=%s", _redact(db_url))
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=settings.db_pool_size,
            pool_pre_ping=True,
            pool_timeout=settings.db_pool_timeout,
        )
        return engine

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_maker is None:
            self._session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
        return self._session_maker

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_maker() as s:  # type: ignore[func-returns-value]
            yield s

    async def ping(self) -> bool:
        try:
            async with self.session() as s:
                await s.execute(text("SELECT 1"))
            return True
        except Exception as exc:  # pragma: no cover - logged for ops
            logger.warning("DB ping failed: %s", exc)
            return False


db = Database()

