from pydantic import BaseModel
from typing import Optional, Dict, Any
from .module import Module
from .chat import ChatMessage


class AgentActionRequest(BaseModel):
    message: str
    module_id: Optional[int] = None
    chat_id: Optional[int] = None


class AgentActionResponse(BaseModel):
    module: Optional[Module] = None
    chat_message: ChatMessage
    agent_decision: Dict[str, Any]
    web_search_performed: bool = False

