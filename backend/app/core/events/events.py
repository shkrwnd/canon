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


class ModuleCreatedEvent(Event):
    """Event fired when a module is created"""
    
    def __init__(self, module_id: int, user_id: int, module_name: str):
        self.module_id = module_id
        self.user_id = user_id
        self.module_name = module_name
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"ModuleCreatedEvent(module_id={self.module_id}, user_id={self.user_id}, name='{self.module_name}')"


class ModuleUpdatedEvent(Event):
    """Event fired when a module is updated"""
    
    def __init__(self, module_id: int, user_id: int, changes: Dict[str, Any]):
        self.module_id = module_id
        self.user_id = user_id
        self.changes = changes  # Dictionary of changed fields
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"ModuleUpdatedEvent(module_id={self.module_id}, user_id={self.user_id}, changes={list(self.changes.keys())})"


class ModuleDeletedEvent(Event):
    """Event fired when a module is deleted"""
    
    def __init__(self, module_id: int, user_id: int, module_name: str):
        self.module_id = module_id
        self.user_id = user_id
        self.module_name = module_name
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"ModuleDeletedEvent(module_id={self.module_id}, user_id={self.user_id}, name='{self.module_name}')"


class AgentActionCompletedEvent(Event):
    """Event fired when an agent action is completed"""
    
    def __init__(
        self,
        user_id: int,
        chat_id: int,
        module_id: Optional[int],
        action_type: str,
        success: bool,
        metadata: Dict[str, Any]
    ):
        self.user_id = user_id
        self.chat_id = chat_id
        self.module_id = module_id
        self.action_type = action_type
        self.success = success
        self.metadata = metadata
        self.timestamp = datetime.utcnow()
    
    def __repr__(self):
        return f"AgentActionCompletedEvent(user_id={self.user_id}, chat_id={self.chat_id}, success={self.success})"

