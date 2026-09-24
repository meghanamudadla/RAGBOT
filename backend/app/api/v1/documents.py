"""
Documents router — endpoints for file upload, listing, and deletion.
Replaces the placeholder router.
"""
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.db.models.user import User
from app.services.document_service import DocumentService
from app.schemas.document import DocumentResponse

router = APIRouter()

def _get_document_service(db: AsyncSession = Depends(get_db)) -> DocumentService:
    """Dependency factory: builds DocumentService from the db session."""
    return DocumentService(db)

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_get_document_service),
) -> DocumentResponse:
    """Upload a new document (PDF, DOCX, TXT), parse, chunk, embed, and store."""
    return await service.upload_document(file, current_user.id)

@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_get_document_service),
) -> list[DocumentResponse]:
    """Retrieve all uploaded documents for the authenticated user."""
    return await service.list_documents(current_user.id)

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_get_document_service),
) -> None:
    """Delete a document and all associated chunks/vectors."""
    await service.delete_document(doc_id, current_user.id)
