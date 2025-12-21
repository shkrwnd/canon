from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.document import Document
from .base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model"""
    
    def __init__(self, db: Session):
        super().__init__(Document, db)
    
    def get_by_project_id(self, project_id: int) -> List[Document]:
        """Get all documents for a project"""
        return self.db.query(Document).filter(Document.project_id == project_id).all()
    
    def get_by_user_id(self, user_id: int) -> List[Document]:
        """Get all documents for a user (across all projects)"""
        return self.db.query(Document).filter(Document.user_id == user_id).all()
    
    def get_by_user_and_id(self, user_id: int, document_id: int) -> Optional[Document]:
        """Get a document by user ID and document ID"""
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
    
    def get_by_project_and_name(self, project_id: int, name: str) -> Optional[Document]:
        """Get a document by project ID and name"""
        return self.db.query(Document).filter(
            Document.project_id == project_id,
            Document.name == name
        ).first()
    
    def get_by_user_and_name_in_project(self, user_id: int, project_id: int, name: str) -> Optional[Document]:
        """Get a document by user ID, project ID, and name"""
        return self.db.query(Document).filter(
            Document.user_id == user_id,
            Document.project_id == project_id,
            Document.name == name
        ).first()
    
    def exists_by_name_in_project(self, project_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a document with the given name exists in the project"""
        query = self.db.query(Document).filter(
            Document.project_id == project_id,
            Document.name == name
        )
        if exclude_id:
            query = query.filter(Document.id != exclude_id)
        return query.first() is not None


