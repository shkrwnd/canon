from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentBase(BaseModel):
    name: str
    standing_instruction: Optional[str] = ""
    content: Optional[str] = ""


class DocumentCreate(DocumentBase):
    project_id: int


class DocumentUpdate(BaseModel):
    name: Optional[str] = None
    standing_instruction: Optional[str] = None
    content: Optional[str] = None


class Document(DocumentBase):
    id: int
    project_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


