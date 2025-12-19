from fastapi import APIRouter, Depends, status
from typing import List
from ...core.security import get_current_user
from ...models import User
from ...schemas import Module as ModuleSchema, ModuleCreate, ModuleUpdate
from ...services import ModuleService
from ..dependencies import get_module_service

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=List[ModuleSchema])
def list_modules(
    current_user: User = Depends(get_current_user),
    module_service: ModuleService = Depends(get_module_service)
):
    """List all modules for the current user"""
    return module_service.list_modules(current_user.id)


@router.post("", response_model=ModuleSchema, status_code=status.HTTP_201_CREATED)
def create_module(
    module_data: ModuleCreate,
    current_user: User = Depends(get_current_user),
    module_service: ModuleService = Depends(get_module_service)
):
    """Create a new module"""
    return module_service.create_module(current_user.id, module_data)


@router.get("/{module_id}", response_model=ModuleSchema)
def get_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    module_service: ModuleService = Depends(get_module_service)
):
    """Get a specific module"""
    return module_service.get_module(current_user.id, module_id)


@router.put("/{module_id}", response_model=ModuleSchema)
def update_module(
    module_id: int,
    module_data: ModuleUpdate,
    current_user: User = Depends(get_current_user),
    module_service: ModuleService = Depends(get_module_service)
):
    """Update a module"""
    return module_service.update_module(current_user.id, module_id, module_data)


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    module_service: ModuleService = Depends(get_module_service)
):
    """Delete a module"""
    module_service.delete_module(current_user.id, module_id)
    return None
