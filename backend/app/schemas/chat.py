from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any
from datetime import datetime
from ..models.chat import MessageRole


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
            return {
                'id': data.id,
                'chat_id': data.chat_id,
                'role': data.role,
                'content': data.content,
                'metadata': data.message_metadata,
                'created_at': data.created_at
            }
        return data

