from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories import ChatRepository
from ..models import Chat, ChatMessage, MessageRole
from ..schemas import ChatCreate, ChatMessageCreate
from ..exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat operations"""
    
    def __init__(self, db: Session):
        self.chat_repo = ChatRepository(db)
        self.db = db
    
    def list_chats(self, user_id: int) -> List[Chat]:
        """List all chats for a user"""
        logger.debug(f"Listing chats for user: {user_id}")
        return self.chat_repo.get_by_user_id(user_id)
    
    def create_chat(self, user_id: int, chat_data: ChatCreate) -> Chat:
        """Create a new chat"""
        logger.info(f"Creating chat for user {user_id}, module_id: {chat_data.module_id}")
        try:
            chat = self.chat_repo.create(
                user_id=user_id,
                module_id=chat_data.module_id,
                title=chat_data.title
            )
            self.chat_repo.commit()
            logger.info(f"Chat created successfully: {chat.id}")
            return chat
        except Exception as e:
            logger.error(f"Error creating chat: {e}")
            self.chat_repo.rollback()
            raise
    
    def get_chat(self, user_id: int, chat_id: int) -> Chat:
        """Get a specific chat"""
        logger.debug(f"Getting chat {chat_id} for user {user_id}")
        chat = self.chat_repo.get_by_user_and_id(user_id, chat_id)
        if not chat:
            raise NotFoundError("Chat", str(chat_id))
        return chat
    
    def get_chat_messages(self, user_id: int, chat_id: int) -> List[ChatMessage]:
        """Get all messages for a chat"""
        logger.debug(f"Getting messages for chat {chat_id}")
        # Verify chat belongs to user
        self.get_chat(user_id, chat_id)
        return self.chat_repo.get_messages_by_chat_id(chat_id)
    
    def add_message(self, user_id: int, chat_id: int, message_data: ChatMessageCreate) -> ChatMessage:
        """Add a message to a chat"""
        logger.debug(f"Adding message to chat {chat_id}")
        
        try:
            chat = self.get_chat(user_id, chat_id)
            
            # Update chat title if it's the first message and title is not set
            if not chat.title and message_data.role == MessageRole.USER:
                self.chat_repo.update_chat_title(
                    chat_id=chat_id,
                    title=message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
                )
            
            message = self.chat_repo.create_message(
                chat_id=chat_id,
                role=message_data.role,
                content=message_data.content,
                message_metadata=message_data.metadata or {}
            )
            
            # Commit both operations together
            self.chat_repo.commit()
            self.db.refresh(message)
            
            logger.debug(f"Message added successfully: {message.id}")
            return message
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            self.chat_repo.rollback()
            raise
