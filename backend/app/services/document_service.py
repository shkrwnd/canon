from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories import DocumentRepository, ProjectRepository
from ..models import User, Document, Project
from ..schemas import DocumentCreate, DocumentUpdate
from ..exceptions import NotFoundError, ValidationError
from ..core.events import event_bus, DocumentCreatedEvent, DocumentUpdatedEvent, DocumentDeletedEvent
import logging

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document operations"""
    
    def __init__(self, db: Session):
        self.document_repo = DocumentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.db = db
    
    def list_documents(self, user_id: int, project_id: int) -> List[Document]:
        """List all documents in a project"""
        logger.debug(f"Listing documents for project {project_id}, user: {user_id}")
        # Verify project belongs to user
        project = self.project_repo.get_by_user_and_id(user_id, project_id)
        if not project:
            raise NotFoundError("Project", str(project_id))
        return self.document_repo.get_by_project_id(project_id)
    
    def get_document(self, user_id: int, document_id: int) -> Document:
        """Get a specific document"""
        logger.debug(f"Getting document {document_id} for user {user_id}")
        document = self.document_repo.get_by_user_and_id(user_id, document_id)
        if not document:
            raise NotFoundError("Document", str(document_id))
        return document
    
    def create_document(self, user_id: int, project_id: int, document_data: DocumentCreate) -> Document:
        """Create a new document in a project"""
        logger.info(f"Creating document '{document_data.name}' in project {project_id} for user {user_id}")
        
        try:
            # Verify project belongs to user
            project = self.project_repo.get_by_user_and_id(user_id, project_id)
            if not project:
                raise NotFoundError("Project", str(project_id))
            
            # Check if document name already exists in project
            if self.document_repo.exists_by_name_in_project(project_id, document_data.name):
                logger.warning(f"Document creation failed: name already exists in project - {document_data.name}")
                raise ValidationError("Document with this name already exists in this project")
            
            document = self.document_repo.create(
                project_id=project_id,
                user_id=user_id,
                name=document_data.name,
                standing_instruction=document_data.standing_instruction or "",
                content=document_data.content or ""
            )
            self.document_repo.commit()
            logger.info(f"Document created successfully: {document.id}")
            
            # Publish event
            event_bus.publish(DocumentCreatedEvent(
                document_id=document.id,
                project_id=document.project_id,
                user_id=user_id,
                document_name=document.name
            ))
            
            return document
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            self.document_repo.rollback()
            raise
    
    def update_document(self, user_id: int, document_id: int, document_data: DocumentUpdate) -> Document:
        """Update a document"""
        logger.info(f"Updating document {document_id} for user {user_id}")
        
        try:
            document = self.document_repo.get_by_user_and_id(user_id, document_id)
            if not document:
                raise NotFoundError("Document", str(document_id))
            
            # Check name conflict if name is being updated
            if document_data.name is not None and document_data.name != document.name:
                if self.document_repo.exists_by_name_in_project(document.project_id, document_data.name, exclude_id=document_id):
                    logger.warning(f"Document update failed: name conflict - {document_data.name}")
                    raise ValidationError("Document with this name already exists in this project")
            
            # Update fields
            update_data = {}
            if document_data.name is not None:
                update_data["name"] = document_data.name
            if document_data.standing_instruction is not None:
                update_data["standing_instruction"] = document_data.standing_instruction
            if document_data.content is not None:
                update_data["content"] = document_data.content
            
            updated_document = self.document_repo.update(document_id, **update_data)
            if updated_document:
                self.document_repo.commit()
                logger.info(f"Document updated successfully: {document_id}")
                
                # Publish event
                event_bus.publish(DocumentUpdatedEvent(
                    document_id=document_id,
                    project_id=document.project_id,
                    user_id=user_id,
                    changes=update_data
                ))
            
            return updated_document
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            self.document_repo.rollback()
            raise
    
    def delete_document(self, user_id: int, document_id: int) -> None:
        """Delete a document"""
        logger.info(f"Deleting document {document_id} for user {user_id}")
        
        try:
            document = self.document_repo.get_by_user_and_id(user_id, document_id)
            if not document:
                raise NotFoundError("Document", str(document_id))
            
            # Store document info before deletion
            document_name = document.name
            project_id = document.project_id
            
            self.document_repo.delete(document_id)
            self.document_repo.commit()
            logger.info(f"Document deleted successfully: {document_id}")
            
            # Publish event
            event_bus.publish(DocumentDeletedEvent(
                document_id=document_id,
                project_id=project_id,
                user_id=user_id,
                document_name=document_name
            ))
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            self.document_repo.rollback()
            raise

