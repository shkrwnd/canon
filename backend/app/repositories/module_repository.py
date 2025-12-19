from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.module import Module
from .base import BaseRepository


class ModuleRepository(BaseRepository[Module]):
    """Repository for Module model"""
    
    def __init__(self, db: Session):
        super().__init__(Module, db)
    
    def get_by_user_id(self, user_id: int) -> List[Module]:
        """Get all modules for a user"""
        return self.db.query(Module).filter(Module.user_id == user_id).all()
    
    def get_by_user_and_id(self, user_id: int, module_id: int) -> Optional[Module]:
        """Get a module by user ID and module ID"""
        return self.db.query(Module).filter(
            Module.id == module_id,
            Module.user_id == user_id
        ).first()
    
    def get_by_user_and_name(self, user_id: int, name: str) -> Optional[Module]:
        """Get a module by user ID and name"""
        return self.db.query(Module).filter(
            Module.user_id == user_id,
            Module.name == name
        ).first()
    
    def exists_by_name(self, user_id: int, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a module with the given name exists for the user"""
        query = self.db.query(Module).filter(
            Module.user_id == user_id,
            Module.name == name
        )
        if exclude_id:
            query = query.filter(Module.id != exclude_id)
        return query.first() is not None

