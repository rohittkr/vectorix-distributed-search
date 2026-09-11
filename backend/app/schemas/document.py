from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    description: str | None = Field(default=None, max_length=4096)
    category: str | None = Field(default=None, max_length=128)
    author: str | None = Field(default=None, max_length=256)
    tags: list[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=16)
    source: str | None = Field(default=None, max_length=256)
    url: str | None = Field(default=None, max_length=2048)
    popularity: float = Field(default=0.0, ge=0.0)
    doc_metadata: dict = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def _dedupe_tags(cls, v: list[str]) -> list[str]:
        return sorted({t.strip().lower() for t in v if t.strip()})

    @field_validator("title", "content")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    content: str | None = Field(default=None, min_length=1)
    description: str | None = None
    category: str | None = None
    author: str | None = None
    tags: list[str] | None = None
    language: str | None = None
    source: str | None = None
    url: str | None = None
    popularity: float | None = Field(default=None, ge=0.0)
    doc_metadata: dict | None = None


class DocumentBulkCreate(BaseModel):
    documents: list[DocumentCreate] = Field(..., min_length=1, max_length=10_000)


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None = None


class DocumentBulkCreateResponse(BaseModel):
    accepted: int
    job_id: str
