"""
Event Handlers

Handlers for events published by services. These handle cross-cutting concerns:
- Logging
- Analytics
- Notifications (future)
- Audit logs (future)
- Monitoring (future)
"""
from .bus import event_bus
from .events import (
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent,
    AgentActionCompletedEvent,
)
import logging

logger = logging.getLogger(__name__)


def handle_document_created(event: DocumentCreatedEvent):
    """Handle document created event"""
    logger.info(
        f"Document created: '{event.document_name}' (id: {event.document_id}) "
        f"in project {event.project_id} by user {event.user_id} at {event.timestamp}"
    )
    # Future: Send notification, create audit log, update analytics, etc.


def handle_document_updated(event: DocumentUpdatedEvent):
    """Handle document updated event"""
    changed_fields = ", ".join(event.changes.keys())
    logger.info(
        f"Document updated: {event.document_id} in project {event.project_id} by user {event.user_id} "
        f"(changed: {changed_fields}) at {event.timestamp}"
    )
    # Future: Track changes, send notifications, update analytics, etc.


def handle_document_deleted(event: DocumentDeletedEvent):
    """Handle document deleted event"""
    logger.info(
        f"Document deleted: '{event.document_name}' (id: {event.document_id}) "
        f"from project {event.project_id} by user {event.user_id} at {event.timestamp}"
    )
    # Future: Create audit log, cleanup related data, etc.


def handle_agent_action_completed(event: AgentActionCompletedEvent):
    """Handle agent action completed event"""
    logger.info(
        f"Agent action completed: user {event.user_id}, chat {event.chat_id}, "
        f"project {event.project_id}, success: {event.success} at {event.timestamp}"
    )
    # Future: Analytics, monitoring, performance tracking, etc.


def register_event_handlers():
    """Register all event handlers with the event bus"""
    event_bus.subscribe(DocumentCreatedEvent, handle_document_created)
    event_bus.subscribe(DocumentUpdatedEvent, handle_document_updated)
    event_bus.subscribe(DocumentDeletedEvent, handle_document_deleted)
    event_bus.subscribe(AgentActionCompletedEvent, handle_agent_action_completed)
    logger.info("Event handlers registered successfully")

