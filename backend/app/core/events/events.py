"""
Event Definitions

Events are used for cross-cutting concerns that can be asynchronous:
- Notifications
- Audit logs
- Analytics
- Monitoring
- Background jobs

Core business logic operations (that need immediate results) should use direct service calls.
"""
from .bus import Event
from typing import Optional, Dict, Any
from datetime import datetime


class DocumentCreatedEvent(Event):
    """Event fired when a document is created"""
    
    def __init__(self, document_id: int, project_id: int, user_id: int, document_name: str):
        self.document_id = document_id
        self.project_id = project_id
        self.user_id = user_id
        self.document_name = document_name
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"DocumentCreatedEvent(document_id={self.document_id}, project_id={self.project_id}, user_id={self.user_id}, name='{self.document_name}')"


class DocumentUpdatedEvent(Event):
    """Event fired when a document is updated"""
    
    def __init__(self, document_id: int, project_id: int, user_id: int, changes: Dict[str, Any]):
        self.document_id = document_id
        self.project_id = project_id
        self.user_id = user_id
        self.changes = changes  # Dictionary of changed fields
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"DocumentUpdatedEvent(document_id={self.document_id}, project_id={self.project_id}, user_id={self.user_id}, changes={list(self.changes.keys())})"


class DocumentDeletedEvent(Event):
    """Event fired when a document is deleted"""
    
    def __init__(self, document_id: int, project_id: int, user_id: int, document_name: str):
        self.document_id = document_id
        self.project_id = project_id
        self.user_id = user_id
        self.document_name = document_name
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"DocumentDeletedEvent(document_id={self.document_id}, project_id={self.project_id}, user_id={self.user_id}, name='{self.document_name}')"


class AgentActionCompletedEvent(Event):
    """Event fired when an agent action is completed"""
    
    def __init__(
        self,
        user_id: int,
        chat_id: int,
        project_id: Optional[int],
        document_id: Optional[int] = None,
        action_type: str = "agent_action",
        success: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.chat_id = chat_id
        self.project_id = project_id
        self.document_id = document_id
        self.action_type = action_type
        self.success = success
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"AgentActionCompletedEvent(user_id={self.user_id}, chat_id={self.chat_id}, project_id={self.project_id}, document_id={self.document_id}, success={self.success})"

