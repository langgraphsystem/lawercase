from __future__ import annotations

import asyncio
import pathlib

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.engine import db


async def apply_migrations() -> None:
    base = pathlib.Path(__file__).parent
    init_sql = (base / "0001_init.sql").read_text(encoding="utf-8")
    async with db.session() as session:  # type: AsyncSession
        await session.execute(text(init_sql))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(apply_migrations())

