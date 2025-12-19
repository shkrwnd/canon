from fastapi import HTTPException, status


class CanonException(HTTPException):
    """Base exception for Canon application"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: dict = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

