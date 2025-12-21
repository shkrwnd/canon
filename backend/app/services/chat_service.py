from typing import List, Optional
from sqlalchemy.orm import Session
from ..repositories import ChatRepository
from ..models import Chat, ChatMessage, MessageRole
from ..schemas import ChatCreate, ChatMessageCreate
from ..exceptions import NotFoundError
from ..core.telemetry import get_tracer
from opentelemetry import trace
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


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
        """Create a new chat for a project"""
        logger.info(f"Creating chat for user {user_id}, project_id: {chat_data.project_id}")
        with tracer.start_as_current_span("chat.create_chat") as span:
            span.set_attribute("chat.user_id", user_id)
            span.set_attribute("chat.project_id", chat_data.project_id)
            try:
                chat = self.chat_repo.create(
                    user_id=user_id,
                    project_id=chat_data.project_id,
                    title=chat_data.title
                )
                self.chat_repo.commit()
                logger.info(f"Chat created successfully: {chat.id}")
                span.set_attribute("chat.id", chat.id)
                span.set_attribute("chat.created", True)
                return chat
            except Exception as e:
                logger.error(f"Error creating chat: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                self.chat_repo.rollback()
                raise
    
    def get_chat(self, user_id: int, chat_id: int) -> Chat:
        """Get a specific chat"""
        logger.debug(f"Getting chat {chat_id} for user {user_id}")
        chat = self.chat_repo.get_by_user_and_id(user_id, chat_id)
        if not chat:
            raise NotFoundError("Chat", str(chat_id))
        return chat
    
    def get_chat_by_project(self, user_id: int, project_id: int) -> Optional[Chat]:
        """Get the chat for a project (returns most recent if multiple exist)"""
        logger.debug(f"Getting chat for user {user_id}, project {project_id}")
        chat = self.chat_repo.get_by_user_and_project(user_id, project_id)
        if chat:
            return chat
        # If no chat found, return None (caller can create one if needed)
        return None
    
    def get_chat_messages(self, user_id: int, chat_id: int) -> List[ChatMessage]:
        """Get all messages for a chat"""
        logger.debug(f"Getting messages for chat {chat_id}")
        # Verify chat belongs to user
        self.get_chat(user_id, chat_id)
        return self.chat_repo.get_messages_by_chat_id(chat_id)
    
    def add_message(self, user_id: int, chat_id: int, message_data: ChatMessageCreate) -> ChatMessage:
        """Add a message to a chat"""
        logger.debug(f"Adding message to chat {chat_id}")
        
        with tracer.start_as_current_span("chat.add_message") as span:
            span.set_attribute("chat.user_id", user_id)
            span.set_attribute("chat.chat_id", chat_id)
            span.set_attribute("message.role", message_data.role.value if hasattr(message_data.role, 'value') else str(message_data.role))
            span.set_attribute("message.content_length", len(message_data.content))
            
            try:
                chat = self.get_chat(user_id, chat_id)
                
                # Update chat title if it's the first message and title is not set
                if not chat.title and message_data.role == MessageRole.USER:
                    with tracer.start_as_current_span("chat.update_title") as title_span:
                        title_span.set_attribute("db.operation", "update_chat_title")
                        self.chat_repo.update_chat_title(
                            chat_id=chat_id,
                            title=message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
                        )
                
                with tracer.start_as_current_span("chat.create_message") as msg_span:
                    msg_span.set_attribute("db.operation", "create_message")
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
                    msg_span.set_attribute("message.id", message.id)
                    span.set_attribute("message.id", message.id)
                    return message
            except Exception as e:
                logger.error(f"Error adding message: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                self.chat_repo.rollback()
                raise
