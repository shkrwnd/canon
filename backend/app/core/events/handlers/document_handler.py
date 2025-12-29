"""
Document Event Handler

Handles all document-related events:
- DocumentCreatedEvent
- DocumentUpdatedEvent
- DocumentDeletedEvent
"""
from ..events import (
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent,
)
import logging

logger = logging.getLogger(__name__)


class DocumentEventHandler:
    """Handler for document-related events"""
    
    def handle_created(self, event: DocumentCreatedEvent):
        """Handle document created event"""
        self._log_created(event)
        self._track_analytics(event)
        self._create_audit_log(event)
        # Future: Send notification, etc.
    
    def handle_updated(self, event: DocumentUpdatedEvent):
        """Handle document updated event"""
        self._log_updated(event)
        self._track_analytics(event)
        self._create_audit_log(event)
        # Future: Send notification, track changes, etc.
    
    def handle_deleted(self, event: DocumentDeletedEvent):
        """Handle document deleted event"""
        self._log_deleted(event)
        self._track_analytics(event)
        self._create_audit_log(event)
        self._cleanup_related_data(event)
        # Future: Send notification, etc.
    
    def _log_created(self, event: DocumentCreatedEvent):
        """Log document creation"""
        logger.info(
            f"Document created: '{event.document_name}' (id: {event.document_id}) "
            f"in project {event.project_id} by user {event.user_id} at {event.timestamp}"
        )
    
    def _log_updated(self, event: DocumentUpdatedEvent):
        """Log document update with change details"""
        changed_fields = ", ".join(event.changes.keys())
        
        # Format the actual changes with values
        change_details = []
        for field, value in event.changes.items():
            if field == "content" and isinstance(value, str):
                # Truncate content to first 100 characters for readability
                content_preview = value[:100] + "..." if len(value) > 100 else value
                change_details.append(f"{field}='{content_preview}'")
            else:
                # For other fields, show the value (truncate if too long)
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                change_details.append(f"{field}={value_str}")
        
        changes_summary = "; ".join(change_details)
        
        logger.info(
            f"Document updated: {event.document_id} in project {event.project_id} by user {event.user_id} "
            f"(changed fields: {changed_fields}) at {event.timestamp}\n"
            f"  Changes: {changes_summary}"
        )
    
    def _log_deleted(self, event: DocumentDeletedEvent):
        """Log document deletion"""
        logger.info(
            f"Document deleted: '{event.document_name}' (id: {event.document_id}) "
            f"from project {event.project_id} by user {event.user_id} at {event.timestamp}"
        )
    
    def _track_analytics(self, event):
        """Track analytics for document events"""
        # Future: Send to analytics service
        pass
    
    def _create_audit_log(self, event):
        """Create audit log entry"""
        # Future: Store in audit log database
        pass
    
    def _cleanup_related_data(self, event: DocumentDeletedEvent):
        """Cleanup data related to deleted document"""
        # Future: Cleanup related data (chats, messages, etc.)
        pass


