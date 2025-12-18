from pydantic import BaseModel, EmailStr, Field, field_serializer, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import MessageRole


# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# User Schemas
class UserBase(BaseModel):
    email: str


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Module Schemas
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


# Chat Schemas
class ChatBase(BaseModel):
    module_id: Optional[int] = None
    title: Optional[str] = None


class ChatCreate(ChatBase):
    pass


class Chat(ChatBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Chat Message Schemas
class ChatMessageBase(BaseModel):
    content: str
    role: MessageRole
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int
    chat_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True
    
    @model_validator(mode='before')
    @classmethod
    def map_message_metadata(cls, data):
        """Map message_metadata attribute to metadata field"""
        if isinstance(data, dict) and 'message_metadata' in data:
            data['metadata'] = data.pop('message_metadata')
        elif hasattr(data, 'message_metadata'):
            # Handle ORM object
            return {
                'id': data.id,
                'chat_id': data.chat_id,
                'role': data.role,
                'content': data.content,
                'metadata': data.message_metadata,
                'created_at': data.created_at
            }
        return data


# Agent Schemas
class AgentActionRequest(BaseModel):
    message: str
    module_id: Optional[int] = None
    chat_id: Optional[int] = None


class AgentActionResponse(BaseModel):
    module: Optional[Module] = None
    chat_message: ChatMessage
    agent_decision: Dict[str, Any]
    web_search_performed: bool = False

