from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ...models import User, Module
from ...schemas import Module as ModuleSchema, ModuleCreate, ModuleUpdate
from ...auth import get_current_user

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=List[ModuleSchema])
def list_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all modules for the current user"""
    modules = db.query(Module).filter(Module.user_id == current_user.id).all()
    return modules


@router.post("", response_model=ModuleSchema, status_code=status.HTTP_201_CREATED)
def create_module(
    module_data: ModuleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new module"""
    # Check if module name already exists for this user
    existing = db.query(Module).filter(
        Module.user_id == current_user.id,
        Module.name == module_data.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Module with this name already exists"
        )
    
    new_module = Module(
        user_id=current_user.id,
        name=module_data.name,
        standing_instruction=module_data.standing_instruction or "",
        content=module_data.content or ""
    )
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module


@router.get("/{module_id}", response_model=ModuleSchema)
def get_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific module"""
    module = db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == current_user.id
    ).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    return module


@router.put("/{module_id}", response_model=ModuleSchema)
def update_module(
    module_id: int,
    module_data: ModuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a module (manual edit - overrides agent output)"""
    module = db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == current_user.id
    ).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    
    # Update fields if provided
    if module_data.name is not None:
        # Check if new name conflicts with existing module
        existing = db.query(Module).filter(
            Module.user_id == current_user.id,
            Module.name == module_data.name,
            Module.id != module_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Module with this name already exists"
            )
        module.name = module_data.name
    
    if module_data.standing_instruction is not None:
        module.standing_instruction = module_data.standing_instruction
    
    if module_data.content is not None:
        module.content = module_data.content
    
    db.commit()
    db.refresh(module)
    return module


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a module"""
    module = db.query(Module).filter(
        Module.id == module_id,
        Module.user_id == current_user.id
    ).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module not found"
        )
    
    db.delete(module)
    db.commit()
    return None



