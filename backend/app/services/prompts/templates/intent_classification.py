"""
Intent Classification Template

Template for classifying user intent (conversation, edit, create, clarify).
"""

from typing import Dict, Any
from .base import PromptTemplate
from ..utils import build_conversation_context


class IntentClassificationTemplate(PromptTemplate):
    """Template for intent classification prompts."""
    name = "intent_classification"
    version = "v1"
    
    def __init__(self, prompt_version: str = "contextual"):
        """
        Initialize template.
        
        Args:
            prompt_version: "contextual" or "rule_based"
        """
        self.prompt_version = prompt_version
    
    def render(self, policy_text: str, runtime: Dict[str, Any]) -> str:
        """Render intent classification prompt."""
        user_message = runtime["user_message"]
        documents = runtime.get("documents", [])
        project_context = runtime.get("project_context")
        chat_history = runtime.get("chat_history", [])
        
        # Build project info
        project_info = ""
        if project_context:
            description = project_context.get('description') or ''
            description_preview = description[:100] if description else ''
            project_info = f"Project: {project_context.get('name', 'Unknown')} - {description_preview}"
        
        # Build document list
        doc_names = [d['name'] for d in documents[:5]] if documents else []
        doc_list = ", ".join(doc_names) if doc_names else "None"
        
        # Build conversation context
        from app.config import settings
        history_window = getattr(settings, 'intent_classification_history_window', 20)
        conversation_context = build_conversation_context(chat_history, window=history_window)
        
        # Build task
        task = f"""Classify the user's intent based on their message and the conversation context.

CONVERSATION HISTORY:
{conversation_context}

CURRENT MESSAGE: "{user_message}"

PROJECT CONTEXT:
{project_info}
Documents: {doc_list}"""
        
        # Build output format
        output_format = """{
    "action": "UPDATE_DOCUMENT | SHOW_DOCUMENT | CREATE_DOCUMENT | ANSWER_ONLY | LIST_DOCUMENTS | NEEDS_CLARIFICATION",
    "targets": [
        {
            "document_name": "Python Guide",
            "summary": "Brief description of why this document is relevant (what it contains that matches the user's request)",
            "role": "primary"
        }
    ],
    "new_document": { "name": "optional document name" },
    "confidence": 0.0-1.0,
    "intent_statement": "What user wants in CURRENT MESSAGE only (use history for context, not for intent)"
}"""
        
        # Render using policy structure
        return f"""{policy_text}

TASK:
{task}

OUTPUT FORMAT:
{output_format}"""
