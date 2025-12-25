"""
Event Handler Classes and Registration

Each event type has a dedicated handler class that processes the event
and handles all related concerns (logging, analytics, notifications, etc.)
"""
from .document_handler import DocumentEventHandler
from .agent_handler import AgentEventHandler
from ..bus import event_bus
from ..events import (
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent,
    AgentActionCompletedEvent,
)
import logging

logger = logging.getLogger(__name__)

# Initialize handler instances
document_handler = DocumentEventHandler()
agent_handler = AgentEventHandler()


def handle_document_created(event: DocumentCreatedEvent):
    """Handle document created event - delegates to DocumentEventHandler"""
    document_handler.handle_created(event)


def handle_document_updated(event: DocumentUpdatedEvent):
    """Handle document updated event - delegates to DocumentEventHandler"""
    document_handler.handle_updated(event)


def handle_document_deleted(event: DocumentDeletedEvent):
    """Handle document deleted event - delegates to DocumentEventHandler"""
    document_handler.handle_deleted(event)


def handle_agent_action_completed(event: AgentActionCompletedEvent):
    """Handle agent action completed event - delegates to AgentEventHandler"""
    agent_handler.handle_action_completed(event)


def register_event_handlers():
    """Register all event handlers with the event bus"""
    event_bus.subscribe(DocumentCreatedEvent, handle_document_created)
    event_bus.subscribe(DocumentUpdatedEvent, handle_document_updated)
    event_bus.subscribe(DocumentDeletedEvent, handle_document_deleted)
    event_bus.subscribe(AgentActionCompletedEvent, handle_agent_action_completed)
    logger.info("Event handlers registered successfully")


__all__ = [
    "DocumentEventHandler",
    "AgentEventHandler",
    "register_event_handlers",
]

