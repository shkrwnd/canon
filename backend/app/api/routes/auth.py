from fastapi import APIRouter, Depends, status
from ...schemas import UserRegister, UserLogin, Token
from ...services import AuthService
from ..dependencies import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    return auth_service.register(user_data)


@router.post("/login", response_model=Token)
def login(
    user_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login user and return JWT token"""
    return auth_service.login(user_data)
