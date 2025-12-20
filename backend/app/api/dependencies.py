"""
Dependency Injection Container for API Routes

This module provides centralized service creation and dependency injection
for all API routes. This eliminates repetitive service instantiation and
makes it easy to add cross-cutting concerns like caching, logging, and metrics.
"""
from functools import lru_cache
from fastapi import Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services import (
    AuthService,
    ModuleService,
    ChatService,
    AgentService,
    LLMService
)
from ..clients import LLMProviderFactory


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """
    Get AuthService instance
    
    Args:
        db: Database session (injected by FastAPI)
    
    Returns:
        AuthService instance
    """
    return AuthService(db)


def get_module_service(db: Session = Depends(get_db)) -> ModuleService:
    """
    Get ModuleService instance
    
    Args:
        db: Database session (injected by FastAPI)
    
    Returns:
        ModuleService instance
    """
    return ModuleService(db)


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """
    Get ChatService instance
    
    Args:
        db: Database session (injected by FastAPI)
    
    Returns:
        ChatService instance
    """
    return ChatService(db)


@lru_cache(maxsize=1)
def _get_llm_service() -> LLMService:
    """
    Internal function to create LLMService (cached for performance)
    
    Returns:
        LLMService instance
    """
    from ..config import settings
    provider = LLMProviderFactory.create_provider()
    return LLMService(
        provider,
        max_concurrent_requests=getattr(settings, 'llm_max_concurrent_requests', 10)
    )


def get_llm_service() -> LLMService:
    """
    Get LLMService instance (singleton pattern)
    
    Returns:
        LLMService instance
    """
    return _get_llm_service()


def get_agent_service(
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
) -> AgentService:
    """
    Get AgentService instance with dependencies
    
    Args:
        db: Database session (injected by FastAPI)
        llm_service: LLM service (injected by dependency)
    
    Returns:
        AgentService instance
    """
    return AgentService(db, llm_service=llm_service)

