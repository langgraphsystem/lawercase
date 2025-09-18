from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Case, CaseItem


async def create_case(session: AsyncSession, *, user_id: Optional[int], title: str, status: str = "open") -> int:
    stmt = insert(Case).values(user_id=user_id, title=title, status=status).returning(Case.id)
    res = await session.execute(stmt)
    return int(res.scalar_one())


async def get_case(session: AsyncSession, case_id: int) -> Optional[Case]:
    res = await session.execute(select(Case).where(Case.id == case_id))
    return res.scalars().first()


async def link_case_items(session: AsyncSession, *, case_id: int, items: Iterable[tuple[str, str]]) -> None:
    payload = [{"case_id": case_id, "item_type": t, "item_id": i} for t, i in items]
    if payload:
        await session.execute(insert(CaseItem), payload)

