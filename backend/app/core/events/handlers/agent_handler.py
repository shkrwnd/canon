"""
Agent Event Handler

Handles agent-related events:
- AgentActionCompletedEvent
"""
from ..events import AgentActionCompletedEvent
import logging

logger = logging.getLogger(__name__)


class AgentEventHandler:
    """Handler for agent-related events"""
    
    def handle_action_completed(self, event: AgentActionCompletedEvent):
        """Handle agent action completed event"""
        self._log_action_completed(event)
        self._track_analytics(event)
        self._track_performance(event)
        self._create_audit_log(event)
        # Future: Send notification, etc.
    
    def _log_action_completed(self, event: AgentActionCompletedEvent):
        """Log agent action completion"""
        logger.info(
            f"Agent action completed: user {event.user_id}, chat {event.chat_id}, "
            f"project {event.project_id}, success: {event.success} at {event.timestamp}"
        )
        
        # Log what changed
        changes = []
        if event.metadata:
            if event.metadata.get("document_created"):
                changes.append("Document created")
            if event.metadata.get("document_updated"):
                changes.append("Document updated")
            if event.metadata.get("web_search_performed"):
                changes.append("Web search performed")
            if event.metadata.get("should_edit"):
                changes.append("Edit action")
            if event.metadata.get("should_create"):
                changes.append("Create action")
            if event.metadata.get("needs_clarification"):
                changes.append("Clarification needed")
            if event.metadata.get("pending_confirmation"):
                changes.append("Confirmation pending")
            
            # Log detailed change information if available
            if event.metadata.get("intent_statement"):
                logger.info(f"Intent: {event.metadata.get('intent_statement')}")
            if event.metadata.get("change_summary"):
                logger.info(f"Change summary: {event.metadata.get('change_summary')}")
            if event.metadata.get("content_summary"):
                logger.info(f"Content summary: {event.metadata.get('content_summary')}")
        
        if changes:
            logger.info(f"Changes: {', '.join(changes)}")
        
        if event.document_id:
            logger.info(f"Document ID: {event.document_id}")
        
        if event.metadata:
            logger.debug(f"Agent action metadata: {event.metadata}")
    
    def _track_analytics(self, event: AgentActionCompletedEvent):
        """Track analytics for agent actions"""
        # Future: Send to analytics service
        # Track: success rate, action types, response times, etc.
        pass
    
    def _track_performance(self, event: AgentActionCompletedEvent):
        """Track performance metrics"""
        # Future: Track performance metrics
        # Track: response time, token usage, cost, etc.
        pass
    
    def _create_audit_log(self, event: AgentActionCompletedEvent):
        """Create audit log entry"""
        # Future: Store in audit log database
        pass

