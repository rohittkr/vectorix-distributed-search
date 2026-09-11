from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: DocumentCreate) -> Document:
        doc = Document(**data.model_dump())
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def bulk_create(self, items: list[DocumentCreate]) -> list[Document]:
        docs = [Document(**item.model_dump()) for item in items]
        self.session.add_all(docs)
        await self.session.flush()
        return docs

    async def get(self, document_id: str) -> Document | None:
        return await self.session.get(Document, document_id)

    async def update(self, document_id: str, data: DocumentUpdate) -> Document | None:
        doc = await self.get(document_id)
        if doc is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(doc, field, value)
        await self.session.flush()
        return doc

    async def delete(self, document_id: str) -> bool:
        doc = await self.get(document_id)
        if doc is None:
            return False
        await self.session.delete(doc)
        await self.session.flush()
        return True

    async def mark_indexed(self, document_ids: list[str]) -> None:
        if not document_ids:
            return
        await self.session.execute(
            update(Document)
            .where(Document.id.in_(document_ids))
            .values(indexed_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def get_unindexed_batch(self, limit: int, exclude_ids: set[str] | None = None) -> list[Document]:
        """
        Fetch a batch of not-yet-indexed documents.

        `exclude_ids` lets a single indexing-job run skip documents that
        already exhausted their retries earlier in the *same* run --
        without it, a permanently-failing document would be re-fetched
        forever (it stays `indexed_at IS NULL`), causing an infinite loop.
        """
        query = select(Document).where(Document.indexed_at.is_(None))
        if exclude_ids:
            query = query.where(Document.id.notin_(exclude_ids))
        query = query.order_by(Document.created_at).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_batch(self, offset: int, limit: int) -> list[Document]:
        result = await self.session.execute(
            select(Document).order_by(Document.created_at).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Document))
        return int(result.scalar_one())

    async def count_indexed(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Document).where(Document.indexed_at.is_not(None))
        )
        return int(result.scalar_one())
