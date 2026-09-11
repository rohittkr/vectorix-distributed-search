import pytest

from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentUpdate


@pytest.mark.asyncio
async def test_create_and_get_document(db_session):
    repo = DocumentRepository(db_session)
    created = await repo.create(DocumentCreate(title="Hello", content="World"))
    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.title == "Hello"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(db_session):
    repo = DocumentRepository(db_session)
    assert await repo.get("does-not-exist") is None


@pytest.mark.asyncio
async def test_update_document_partial_fields(db_session):
    repo = DocumentRepository(db_session)
    doc = await repo.create(DocumentCreate(title="Old", content="Body"))
    updated = await repo.update(doc.id, DocumentUpdate(title="New"))
    assert updated.title == "New"
    assert updated.content == "Body"  # untouched


@pytest.mark.asyncio
async def test_delete_document(db_session):
    repo = DocumentRepository(db_session)
    doc = await repo.create(DocumentCreate(title="Bye", content="Body"))
    assert await repo.delete(doc.id) is True
    assert await repo.get(doc.id) is None
    assert await repo.delete(doc.id) is False  # already gone


@pytest.mark.asyncio
async def test_bulk_create(db_session):
    repo = DocumentRepository(db_session)
    items = [DocumentCreate(title=f"T{i}", content="C") for i in range(5)]
    docs = await repo.bulk_create(items)
    assert len(docs) == 5
    assert await repo.count_all() == 5


@pytest.mark.asyncio
async def test_mark_indexed_updates_indexed_at_and_unindexed_batch_shrinks(db_session):
    repo = DocumentRepository(db_session)
    items = [DocumentCreate(title=f"T{i}", content="C") for i in range(3)]
    docs = await repo.bulk_create(items)
    ids = [d.id for d in docs]

    unindexed_before = await repo.get_unindexed_batch(10)
    assert len(unindexed_before) == 3

    await repo.mark_indexed(ids[:2])

    unindexed_after = await repo.get_unindexed_batch(10)
    assert len(unindexed_after) == 1
    assert await repo.count_indexed() == 2


@pytest.mark.asyncio
async def test_get_batch_pagination(db_session):
    repo = DocumentRepository(db_session)
    await repo.bulk_create([DocumentCreate(title=f"T{i}", content="C") for i in range(10)])
    page1 = await repo.get_batch(offset=0, limit=4)
    page2 = await repo.get_batch(offset=4, limit=4)
    assert len(page1) == 4
    assert len(page2) == 4
    assert {d.id for d in page1}.isdisjoint({d.id for d in page2})
