from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories import ProjectRepository
from ..models import User, Project
from ..schemas import ProjectCreate, ProjectUpdate
from ..exceptions import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project operations"""
    
    def __init__(self, db: Session):
        self.project_repo = ProjectRepository(db)
        self.db = db
    
    def list_projects(self, user_id: int) -> List[Project]:
        """List all projects for a user"""
        logger.debug(f"Listing projects for user: {user_id}")
        return self.project_repo.get_by_user_id(user_id)
    
    def get_project(self, user_id: int, project_id: int) -> Project:
        """Get a specific project"""
        logger.debug(f"Getting project {project_id} for user {user_id}")
        project = self.project_repo.get_by_user_and_id(user_id, project_id)
        if not project:
            raise NotFoundError("Project", str(project_id))
        return project
    
    def create_project(self, user_id: int, project_data: ProjectCreate) -> Project:
        """Create a new project"""
        logger.info(f"Creating project '{project_data.name}' for user {user_id}")
        
        try:
            # Check if project name already exists
            if self.project_repo.exists_by_name(user_id, project_data.name):
                logger.warning(f"Project creation failed: name already exists - {project_data.name}")
                raise ValidationError("Project with this name already exists")
            
            project = self.project_repo.create(
                user_id=user_id,
                name=project_data.name,
                description=project_data.description or None
            )
            self.project_repo.commit()
            logger.info(f"Project created successfully: {project.id}")
            
            return project
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            self.project_repo.rollback()
            raise
    
    def update_project(self, user_id: int, project_id: int, project_data: ProjectUpdate) -> Project:
        """Update a project"""
        logger.info(f"Updating project {project_id} for user {user_id}")
        
        try:
            project = self.project_repo.get_by_user_and_id(user_id, project_id)
            if not project:
                raise NotFoundError("Project", str(project_id))
            
            # Check name conflict if name is being updated
            if project_data.name is not None and project_data.name != project.name:
                if self.project_repo.exists_by_name(user_id, project_data.name, exclude_id=project_id):
                    logger.warning(f"Project update failed: name conflict - {project_data.name}")
                    raise ValidationError("Project with this name already exists")
            
            # Update fields
            update_data = {}
            if project_data.name is not None:
                update_data["name"] = project_data.name
            if project_data.description is not None:
                update_data["description"] = project_data.description
            
            updated_project = self.project_repo.update(project_id, **update_data)
            if updated_project:
                self.project_repo.commit()
                logger.info(f"Project updated successfully: {project_id}")
            
            return updated_project
        except Exception as e:
            logger.error(f"Error updating project: {e}")
            self.project_repo.rollback()
            raise
    
    def delete_project(self, user_id: int, project_id: int) -> None:
        """Delete a project (cascades to documents and chats)"""
        logger.info(f"Deleting project {project_id} for user {user_id}")
        
        try:
            project = self.project_repo.get_by_user_and_id(user_id, project_id)
            if not project:
                raise NotFoundError("Project", str(project_id))
            
            self.project_repo.delete(project_id)
            self.project_repo.commit()
            logger.info(f"Project deleted successfully: {project_id}")
        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            self.project_repo.rollback()
            raise


