from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from ..core.database import Base
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get a record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.flush()  # Flush instead of commit to allow rollback
        logger.debug(f"Created {self.model.__name__} with id: {instance.id}")
        return instance
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update a record"""
        instance = self.get(id)
        if instance:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(instance, key, value)
            self.db.flush()  # Flush instead of commit to allow rollback
            logger.debug(f"Updated {self.model.__name__} with id: {id}")
        return instance
    
    def delete(self, id: int) -> bool:
        """Delete a record"""
        instance = self.get(id)
        if instance:
            self.db.delete(instance)
            self.db.flush()  # Flush instead of commit to allow rollback
            logger.debug(f"Deleted {self.model.__name__} with id: {id}")
            return True
        return False
    
    def commit(self) -> None:
        """Commit the current transaction"""
        self.db.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        self.db.rollback()
