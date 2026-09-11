from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import DocumentNotFoundError
from app.models.jobs import JobType
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentBulkCreate,
    DocumentBulkCreateResponse,
    DocumentCreate,
    DocumentRead,
    DocumentUpdate,
)
from app.services.indexing_service import IndexingService

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, session: AsyncSession = Depends(get_db)) -> DocumentRead:
    repo = DocumentRepository(session)
    doc = await repo.create(payload)

    indexing_service = IndexingService(session)
    await indexing_service.create_job(JobType.INDEX_DOCUMENT)

    return DocumentRead.model_validate(doc)


@router.post("/documents/bulk", response_model=DocumentBulkCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def bulk_create_documents(
    payload: DocumentBulkCreate, session: AsyncSession = Depends(get_db)
) -> DocumentBulkCreateResponse:
    repo = DocumentRepository(session)
    await repo.bulk_create(payload.documents)

    indexing_service = IndexingService(session)
    job = await indexing_service.create_job(JobType.BULK_INDEX)

    return DocumentBulkCreateResponse(accepted=len(payload.documents), job_id=job.id)


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(document_id: str, session: AsyncSession = Depends(get_db)) -> DocumentRead:
    repo = DocumentRepository(session)
    doc = await repo.get(document_id)
    if doc is None:
        raise DocumentNotFoundError()
    return DocumentRead.model_validate(doc)


@router.put("/documents/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: str, payload: DocumentUpdate, session: AsyncSession = Depends(get_db)
) -> DocumentRead:
    repo = DocumentRepository(session)
    doc = await repo.update(document_id, payload)
    if doc is None:
        raise DocumentNotFoundError()
    return DocumentRead.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, session: AsyncSession = Depends(get_db)) -> None:
    repo = DocumentRepository(session)
    deleted = await repo.delete(document_id)
    if not deleted:
        raise DocumentNotFoundError()
