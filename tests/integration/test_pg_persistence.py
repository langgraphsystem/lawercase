import os
import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _skip_if_no_db(monkeypatch):
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skipping PG integration tests")


async def test_migrations_and_crud():
    from db.migrations.apply import apply_migrations
    from core.db.engine import db
    from core.db.dao_cases import create_case, get_case, link_case_items
    from core.db.dao_documents import create_document, bulk_insert_chunks, get_document

    # Apply minimal migrations
    await apply_migrations()

    # Basic CRUD
    async with db.session() as session:
        case_id = await create_case(session, user_id=None, title="Test Case")
        doc_id = await create_document(session, title="Doc A", case_id=case_id, external_id="ext-1")
        await bulk_insert_chunks(
            session,
            document_id=doc_id,
            chunks=[
                {"chunk_id": "c1", "text": "hello world", "score": 0.5},
                {"chunk_id": "c2", "text": "visa compliance", "score": 0.9},
            ],
        )
        await link_case_items(session, case_id=case_id, items=[("document", str(doc_id))])
        await session.commit()

    # Verify reads
    async with db.session() as session:
        got_case = await get_case(session, case_id)
        assert got_case is not None
        got_doc = await get_document(session, doc_id)
        assert got_doc is not None


async def test_healthz_reports_db_ok():
    from api.routes.health import healthz_payload

    payload = await healthz_payload()
    assert payload["db"] in {"ok", "error"}

