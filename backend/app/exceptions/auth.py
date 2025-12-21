from fastapi import status
from .base import CanonException


class AuthenticationError(CanonException):
    """Exception raised when authentication fails"""
    
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(CanonException):
    """Exception raised when user is not authorized"""
    
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )


