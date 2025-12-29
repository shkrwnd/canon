from fastapi import status
from .base import CanonException


class ValidationError(CanonException):
    """Exception raised when validation fails"""
    
    def __init__(self, detail: str):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST
        )



