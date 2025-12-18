from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...database import get_db
from ...models import User, Chat, ChatMessage, MessageRole
from ...schemas import Chat as ChatSchema, ChatCreate, ChatMessage as ChatMessageSchema, ChatMessageCreate
from ...auth import get_current_user

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=List[ChatSchema])
def list_chats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all chats for the current user"""
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).all()
    return chats


@router.post("", response_model=ChatSchema, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat"""
    new_chat = Chat(
        user_id=current_user.id,
        module_id=chat_data.module_id,
        title=chat_data.title
    )
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return new_chat


@router.get("/{chat_id}/messages", response_model=List[ChatMessageSchema])
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a chat"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).all()
    return messages


@router.post("/{chat_id}/messages", response_model=ChatMessageSchema, status_code=status.HTTP_201_CREATED)
def add_message(
    chat_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a message to a chat"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    new_message = ChatMessage(
        chat_id=chat_id,
        role=message_data.role,
        content=message_data.content,
        message_metadata=message_data.metadata or {}
    )
    db.add(new_message)
    
    # Update chat title if it's the first message and title is not set
    if not chat.title and message_data.role == MessageRole.USER:
        # Use first 50 chars of message as title
        chat.title = message_data.content[:50] + ("..." if len(message_data.content) > 50 else "")
    
    db.commit()
    db.refresh(new_message)
    return new_message

