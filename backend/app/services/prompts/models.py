"""
Pydantic models for structured prompt outputs.

These models define the schema for LLM responses, ensuring
type safety and validation.
"""

from enum import Enum
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field


class IntentAction(str, Enum):
    """Intent action types for classification."""
    UPDATE_DOCUMENT = "UPDATE_DOCUMENT"
    CREATE_DOCUMENT = "CREATE_DOCUMENT"
    DELETE_DOCUMENT = "DELETE_DOCUMENT"
    SHOW_DOCUMENT = "SHOW_DOCUMENT"
    ANSWER_ONLY = "ANSWER_ONLY"
    LIST_DOCUMENTS = "LIST_DOCUMENTS"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class DocumentTarget(BaseModel):
    """Document target for intent classification."""
    document_name: str
    document_id: Optional[int] = None
    summary: Optional[str] = None
    role: Literal["primary", "secondary"] = "primary"


class IntentClassificationResult(BaseModel):
    """Structured output for intent classification."""
    action: IntentAction
    targets: List[DocumentTarget] = Field(default_factory=list)
    new_document: Optional[Dict[str, str]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    intent_statement: str


class AgentDecisionResult(BaseModel):
    """Structured output for agent decision."""
    should_edit: bool = False
    should_create: bool = False
    should_delete: bool = False
    document_id: Optional[int] = None
    document_name: Optional[str] = None
    document_content: Optional[str] = None
    standing_instruction: Optional[str] = None
    edit_scope: Optional[Literal["selective", "full"]] = None
    needs_clarification: bool = False
    pending_confirmation: bool = False
    needs_web_search: bool = False
    search_query: Optional[str] = None
    clarification_question: Optional[str] = None
    confirmation_prompt: Optional[str] = None
    intent_statement: Optional[str] = None
    reasoning: str = ""
    conversational_response: Optional[str] = None
    change_summary: Optional[str] = None
    content_summary: Optional[str] = None
