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
    ModuleCreatedEvent,
    ModuleUpdatedEvent,
    ModuleDeletedEvent,
    AgentActionCompletedEvent,
)
import logging

logger = logging.getLogger(__name__)


def handle_module_created(event: ModuleCreatedEvent):
    """Handle module created event"""
    logger.info(
        f"Module created: '{event.module_name}' (id: {event.module_id}) "
        f"by user {event.user_id} at {event.timestamp}"
    )
    # Future: Send notification, create audit log, update analytics, etc.


def handle_module_updated(event: ModuleUpdatedEvent):
    """Handle module updated event"""
    changed_fields = ", ".join(event.changes.keys())
    logger.info(
        f"Module updated: {event.module_id} by user {event.user_id} "
        f"(changed: {changed_fields}) at {event.timestamp}"
    )
    # Future: Track changes, send notifications, update analytics, etc.


def handle_module_deleted(event: ModuleDeletedEvent):
    """Handle module deleted event"""
    logger.info(
        f"Module deleted: '{event.module_name}' (id: {event.module_id}) "
        f"by user {event.user_id} at {event.timestamp}"
    )
    # Future: Create audit log, cleanup related data, etc.


def handle_agent_action_completed(event: AgentActionCompletedEvent):
    """Handle agent action completed event"""
    logger.info(
        f"Agent action completed: user {event.user_id}, chat {event.chat_id}, "
        f"module {event.module_id}, success: {event.success} at {event.timestamp}"
    )
    # Future: Analytics, monitoring, performance tracking, etc.


def register_event_handlers():
    """Register all event handlers with the event bus"""
    event_bus.subscribe(ModuleCreatedEvent, handle_module_created)
    event_bus.subscribe(ModuleUpdatedEvent, handle_module_updated)
    event_bus.subscribe(ModuleDeletedEvent, handle_module_deleted)
    event_bus.subscribe(AgentActionCompletedEvent, handle_agent_action_completed)
    logger.info("Event handlers registered successfully")

