from fastapi import Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user
from ..models import User


def get_current_user_dependency() -> User:
    """Dependency for getting current user"""
    return Depends(get_current_user)


def get_db_dependency() -> Session:
    """Dependency for getting database session"""
    return Depends(get_db)



