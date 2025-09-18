from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Chunk, Document


async def create_document(
    session: AsyncSession,
    *,
    title: str,
    case_id: Optional[int] = None,
    external_id: Optional[str] = None,
) -> int:
    stmt = insert(Document).values(title=title, case_id=case_id, external_id=external_id).returning(Document.id)
    res = await session.execute(stmt)
    return int(res.scalar_one())


async def bulk_insert_chunks(session: AsyncSession, *, document_id: int, chunks: Iterable[dict]) -> None:
    # chunks: dicts with keys: chunk_id, text, score(optional)
    payload = [{"document_id": document_id, **c} for c in chunks]
    if payload:
        await session.execute(insert(Chunk), payload)


async def get_document(session: AsyncSession, document_id: int) -> Optional[Document]:
    res = await session.execute(select(Document).where(Document.id == document_id))
    return res.scalars().first()

