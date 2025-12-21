from fastapi import APIRouter, Depends, status
from typing import List
from ...core.security import get_current_user
from ...models import User
from ...schemas import Chat as ChatSchema, ChatCreate, ChatMessage as ChatMessageSchema, ChatMessageCreate
from ...services import ChatService
from ..dependencies import get_chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=List[ChatSchema])
def list_chats(
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """List all chats for the current user"""
    return chat_service.list_chats(current_user.id)


@router.post("", response_model=ChatSchema, status_code=status.HTTP_201_CREATED)
def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Create a new chat"""
    return chat_service.create_chat(current_user.id, chat_data)


@router.get("/project/{project_id}", response_model=ChatSchema)
def get_chat_by_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get the chat for a project (creates one if it doesn't exist)"""
    from ...schemas import ChatCreate
    chat = chat_service.get_chat_by_project(current_user.id, project_id)
    if not chat:
        # Create a new chat if one doesn't exist
        chat = chat_service.create_chat(current_user.id, ChatCreate(project_id=project_id))
    return chat


@router.get("/{chat_id}/messages", response_model=List[ChatMessageSchema])
def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get all messages for a chat"""
    return chat_service.get_chat_messages(current_user.id, chat_id)


@router.post("/{chat_id}/messages", response_model=ChatMessageSchema, status_code=status.HTTP_201_CREATED)
def add_message(
    chat_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Add a message to a chat"""
    return chat_service.add_message(current_user.id, chat_id, message_data)
