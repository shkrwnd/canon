from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ModuleBase(BaseModel):
    name: str
    standing_instruction: Optional[str] = ""
    content: Optional[str] = ""


class ModuleCreate(ModuleBase):
    pass


class ModuleUpdate(BaseModel):
    name: Optional[str] = None
    standing_instruction: Optional[str] = None
    content: Optional[str] = None


class Module(ModuleBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



