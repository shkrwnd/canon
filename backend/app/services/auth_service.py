from typing import Optional
from sqlalchemy.orm import Session
from datetime import timedelta
from ..repositories import UserRepository
from ..core.security import (
    get_password_hash,
    authenticate_user,
    create_access_token,
)
from ..models import User
from ..schemas import UserRegister, UserLogin, Token
from ..exceptions import ValidationError, AuthenticationError
from ..config import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.db = db
    
    def register(self, user_data: UserRegister) -> Token:
        """Register a new user"""
        logger.info(f"Attempting to register user: {user_data.email}")
        
        try:
            # Check if user already exists
            existing_user = self.user_repo.get_by_email(user_data.email)
            if existing_user:
                logger.warning(f"Registration failed: email already exists - {user_data.email}")
                raise ValidationError("Email already registered")
            
            # Create new user
            hashed_password = get_password_hash(user_data.password)
            new_user = self.user_repo.create(
                email=user_data.email,
                hashed_password=hashed_password
            )
            self.user_repo.commit()
            
            logger.info(f"User registered successfully: {new_user.email}")
            
            # Create access token
            access_token_expires = timedelta(hours=settings.jwt_expiration_hours)
            access_token = create_access_token(
                data={"sub": new_user.email},
                expires_delta=access_token_expires
            )
            
            return Token(access_token=access_token, token_type="bearer")
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            self.user_repo.rollback()
            raise
    
    def login(self, user_data: UserLogin) -> Token:
        """Login user and return JWT token"""
        logger.info(f"Attempting login for: {user_data.email}")
        
        user = authenticate_user(self.db, user_data.email, user_data.password)
        if not user:
            logger.warning(f"Login failed for: {user_data.email}")
            raise AuthenticationError("Invalid email or password")
        
        logger.info(f"User logged in successfully: {user.email}")
        
        # Create access token
        access_token_expires = timedelta(hours=settings.jwt_expiration_hours)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
