from pydantic import BaseModel
from typing import Optional, Dict, Any
from .document import Document
from .chat import ChatMessage


class AgentActionRequest(BaseModel):
    message: str
    project_id: int
    document_id: Optional[int] = None
    chat_id: Optional[int] = None


class AgentActionResponse(BaseModel):
    document: Optional[Document] = None
    chat_message: ChatMessage
    agent_decision: Dict[str, Any]
    web_search_performed: bool = False

