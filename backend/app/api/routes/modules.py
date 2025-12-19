from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from ...core.database import get_db
from ...core.security import get_current_user
from ...models import User
from ...schemas import Module as ModuleSchema, ModuleCreate, ModuleUpdate
from ...services import ModuleService

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=List[ModuleSchema])
def list_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all modules for the current user"""
    module_service = ModuleService(db)
    return module_service.list_modules(current_user.id)


@router.post("", response_model=ModuleSchema, status_code=status.HTTP_201_CREATED)
def create_module(
    module_data: ModuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new module"""
    module_service = ModuleService(db)
    return module_service.create_module(current_user.id, module_data)


@router.get("/{module_id}", response_model=ModuleSchema)
def get_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific module"""
    module_service = ModuleService(db)
    return module_service.get_module(current_user.id, module_id)


@router.put("/{module_id}", response_model=ModuleSchema)
def update_module(
    module_id: int,
    module_data: ModuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a module"""
    module_service = ModuleService(db)
    return module_service.update_module(current_user.id, module_id, module_data)


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a module"""
    module_service = ModuleService(db)
    module_service.delete_module(current_user.id, module_id)
    return None
