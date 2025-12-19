from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories import ModuleRepository
from ..models import User, Module
from ..schemas import ModuleCreate, ModuleUpdate
from ..exceptions import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)


class ModuleService:
    """Service for module operations"""
    
    def __init__(self, db: Session):
        self.module_repo = ModuleRepository(db)
        self.db = db
    
    def list_modules(self, user_id: int) -> List[Module]:
        """List all modules for a user"""
        logger.debug(f"Listing modules for user: {user_id}")
        return self.module_repo.get_by_user_id(user_id)
    
    def get_module(self, user_id: int, module_id: int) -> Module:
        """Get a specific module"""
        logger.debug(f"Getting module {module_id} for user {user_id}")
        module = self.module_repo.get_by_user_and_id(user_id, module_id)
        if not module:
            raise NotFoundError("Module", str(module_id))
        return module
    
    def create_module(self, user_id: int, module_data: ModuleCreate) -> Module:
        """Create a new module"""
        logger.info(f"Creating module '{module_data.name}' for user {user_id}")
        
        try:
            # Check if module name already exists
            if self.module_repo.exists_by_name(user_id, module_data.name):
                logger.warning(f"Module creation failed: name already exists - {module_data.name}")
                raise ValidationError("Module with this name already exists")
            
            module = self.module_repo.create(
                user_id=user_id,
                name=module_data.name,
                standing_instruction=module_data.standing_instruction or "",
                content=module_data.content or ""
            )
            self.module_repo.commit()
            logger.info(f"Module created successfully: {module.id}")
            return module
        except Exception as e:
            logger.error(f"Error creating module: {e}")
            self.module_repo.rollback()
            raise
    
    def update_module(self, user_id: int, module_id: int, module_data: ModuleUpdate) -> Module:
        """Update a module"""
        logger.info(f"Updating module {module_id} for user {user_id}")
        
        try:
            module = self.module_repo.get_by_user_and_id(user_id, module_id)
            if not module:
                raise NotFoundError("Module", str(module_id))
            
            # Check name conflict if name is being updated
            if module_data.name is not None and module_data.name != module.name:
                if self.module_repo.exists_by_name(user_id, module_data.name, exclude_id=module_id):
                    logger.warning(f"Module update failed: name conflict - {module_data.name}")
                    raise ValidationError("Module with this name already exists")
            
            # Update fields
            update_data = {}
            if module_data.name is not None:
                update_data["name"] = module_data.name
            if module_data.standing_instruction is not None:
                update_data["standing_instruction"] = module_data.standing_instruction
            if module_data.content is not None:
                update_data["content"] = module_data.content
            
            updated_module = self.module_repo.update(module_id, **update_data)
            if updated_module:
                self.module_repo.commit()
                logger.info(f"Module updated successfully: {module_id}")
            return updated_module
        except Exception as e:
            logger.error(f"Error updating module: {e}")
            self.module_repo.rollback()
            raise
    
    def delete_module(self, user_id: int, module_id: int) -> None:
        """Delete a module"""
        logger.info(f"Deleting module {module_id} for user {user_id}")
        
        try:
            module = self.module_repo.get_by_user_and_id(user_id, module_id)
            if not module:
                raise NotFoundError("Module", str(module_id))
            
            self.module_repo.delete(module_id)
            self.module_repo.commit()
            logger.info(f"Module deleted successfully: {module_id}")
        except Exception as e:
            logger.error(f"Error deleting module: {e}")
            self.module_repo.rollback()
            raise
