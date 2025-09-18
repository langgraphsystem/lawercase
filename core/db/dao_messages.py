from __future__ import annotations

from typing import Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Message


async def create_message(session: AsyncSession, *, case_id: Optional[int], sender: str, content: str) -> int:
    stmt = insert(Message).values(case_id=case_id, sender=sender, content=content).returning(Message.id)
    res = await session.execute(stmt)
    return int(res.scalar_one())

