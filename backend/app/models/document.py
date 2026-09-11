import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _json_type():
    # JSONB on Postgres, portable JSON on sqlite (used only in unit tests).
    return JSONB().with_variant(JSON(), "sqlite")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """
    Canonical, durable record for a searchable document.

    Postgres is the system of record; Elasticsearch holds a derived,
    eventually-consistent search index built from these rows by the
    async indexing pipeline.
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_category", "category"),
        Index("ix_documents_author", "author"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_indexed_at", "indexed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tags: Mapped[list] = mapped_column(_json_type(), default=list)
    language: Mapped[str] = mapped_column(String(16), default="en")
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    popularity: Mapped[float] = mapped_column(Float, default=0.0)
    doc_metadata: Mapped[dict] = mapped_column(_json_type(), default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_search_document(self) -> dict:
        """Shape used when bulk-indexing into Elasticsearch."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "description": self.description or "",
            "category": self.category,
            "author": self.author,
            "tags": self.tags or [],
            "language": self.language,
            "source": self.source,
            "url": self.url,
            "popularity": self.popularity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
