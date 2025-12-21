from fastapi import APIRouter, Depends, status
from typing import List
from ...core.security import get_current_user
from ...models import User
from ...schemas import Document as DocumentSchema, DocumentCreate, DocumentUpdate
from ...services import DocumentService
from ..dependencies import get_document_service

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=List[DocumentSchema])
def list_documents(
    project_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """List all documents in a project"""
    return document_service.list_documents(current_user.id, project_id)


@router.post("", response_model=DocumentSchema, status_code=status.HTTP_201_CREATED)
def create_document(
    project_id: int,
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Create a new document in a project"""
    # Ensure project_id in document_data matches the path parameter
    document_data.project_id = project_id
    return document_service.create_document(current_user.id, project_id, document_data)


@router.get("/{document_id}", response_model=DocumentSchema)
def get_document(
    project_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get a specific document"""
    document = document_service.get_document(current_user.id, document_id)
    # Verify document belongs to the project
    if document.project_id != project_id:
        from ...exceptions import NotFoundError
        raise NotFoundError("Document", str(document_id))
    return document


@router.put("/{document_id}", response_model=DocumentSchema)
def update_document(
    project_id: int,
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Update a document"""
    document = document_service.get_document(current_user.id, document_id)
    # Verify document belongs to the project
    if document.project_id != project_id:
        from ...exceptions import NotFoundError
        raise NotFoundError("Document", str(document_id))
    return document_service.update_document(current_user.id, document_id, document_data)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    project_id: int,
    document_id: int,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Delete a document"""
    document = document_service.get_document(current_user.id, document_id)
    # Verify document belongs to the project
    if document.project_id != project_id:
        from ...exceptions import NotFoundError
        raise NotFoundError("Document", str(document_id))
    document_service.delete_document(current_user.id, document_id)
    return None

