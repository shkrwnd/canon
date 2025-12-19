from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.chat import Chat, ChatMessage
from .base import BaseRepository


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat model"""
    
    def __init__(self, db: Session):
        super().__init__(Chat, db)
    
    def get_by_user_id(self, user_id: int) -> List[Chat]:
        """Get all chats for a user"""
        return self.db.query(Chat).filter(Chat.user_id == user_id).all()
    
    def get_by_user_and_id(self, user_id: int, chat_id: int) -> Optional[Chat]:
        """Get a chat by user ID and chat ID"""
        return self.db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == user_id
        ).first()
    
    def get_by_module_id(self, module_id: int) -> List[Chat]:
        """Get all chats for a module"""
        return self.db.query(Chat).filter(Chat.module_id == module_id).all()
    
    def get_messages_by_chat_id(self, chat_id: int) -> List[ChatMessage]:
        """Get all messages for a chat"""
        return self.db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).all()
    
    def create_message(self, chat_id: int, **kwargs) -> ChatMessage:
        """Create a new chat message"""
        message = ChatMessage(chat_id=chat_id, **kwargs)
        self.db.add(message)
        self.db.flush()  # Flush instead of commit to allow rollback
        return message
    
    def update_chat_title(self, chat_id: int, title: str) -> Optional[Chat]:
        """Update chat title"""
        return self.update(chat_id, title=title)
