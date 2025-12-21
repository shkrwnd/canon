from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.project import Project
from .base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model"""
    
    def __init__(self, db: Session):
        super().__init__(Project, db)
    
    def get_by_user_id(self, user_id: int) -> List[Project]:
        """Get all projects for a user"""
        return self.db.query(Project).filter(Project.user_id == user_id).all()
    
    def get_by_user_and_id(self, user_id: int, project_id: int) -> Optional[Project]:
        """Get a project by user ID and project ID"""
        return self.db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id
        ).first()
    
    def get_by_user_and_name(self, user_id: int, name: str) -> Optional[Project]:
        """Get a project by user ID and name"""
        return self.db.query(Project).filter(
            Project.user_id == user_id,
            Project.name == name
        ).first()
    
    def exists_by_name(self, user_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a project with the given name exists for the user"""
        query = self.db.query(Project).filter(
            Project.user_id == user_id,
            Project.name == name
        )
        if exclude_id:
            query = query.filter(Project.id != exclude_id)
        return query.first() is not None


