from fastapi import APIRouter, Depends, status
from typing import List
from ...core.security import get_current_user
from ...models import User
from ...schemas import Project as ProjectSchema, ProjectCreate, ProjectUpdate
from ...services import ProjectService
from ..dependencies import get_project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectSchema])
def list_projects(
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """List all projects for the current user"""
    return project_service.list_projects(current_user.id)


@router.post("", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Create a new project"""
    return project_service.create_project(current_user.id, project_data)


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Get a specific project"""
    return project_service.get_project(current_user.id, project_id)


@router.put("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Update a project"""
    return project_service.update_project(current_user.id, project_id, project_data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """Delete a project (cascades to documents and chats)"""
    project_service.delete_project(current_user.id, project_id)
    return None



