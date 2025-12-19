from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from ...core.database import get_db
from ...core.security import get_current_user
from ...models import User
from ...schemas import Chat as ChatSchema, ChatCreate, ChatMessage as ChatMessageSchema, ChatMessageCreate
from ...services import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=List[ChatSchema])
def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chats for the current user"""
    chat_service = ChatService(db)
    return chat_service.list_chats(current_user.id)


@router.post("", response_model=ChatSchema, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat"""
    chat_service = ChatService(db)
    return chat_service.create_chat(current_user.id, chat_data)


@router.get("/{chat_id}/messages", response_model=List[ChatMessageSchema])
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a chat"""
    chat_service = ChatService(db)
    return chat_service.get_chat_messages(current_user.id, chat_id)


@router.post("/{chat_id}/messages", response_model=ChatMessageSchema, status_code=status.HTTP_201_CREATED)
def add_message(
    chat_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a message to a chat"""
    chat_service = ChatService(db)
    return chat_service.add_message(current_user.id, chat_id, message_data)
