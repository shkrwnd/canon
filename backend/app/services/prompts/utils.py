"""
Utility functions for prompt generation.

Helper functions for date calculations, document formatting,
and conversation context building.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


def get_current_date_context() -> Dict[str, Any]:
    """
    Get current date context for prompts.
    
    Returns:
        Dictionary with current_year, current_month, current_date_str,
        and most_recent_december_year
    """
    now = datetime.now()
    return {
        "current_year": now.year,
        "current_month": now.month,
        "current_date_str": now.strftime('%B %d, %Y'),
        "most_recent_december_year": now.year - 1 if now.month < 12 else now.year
    }


def build_documents_list(documents: list, max_length: int = 2000) -> str:
    """
    Build compressed document list for prompts.
    
    Args:
        documents: List of document dictionaries with 'id', 'name', 'content'
        max_length: Maximum length for document preview
    
    Returns:
        Formatted string with document list
    """
    if not documents:
        return "No documents available"
    
    docs = []
    for d in documents:
        content = d.get('content', '')
        name = d.get('name', 'Unnamed')
        doc_id = d.get('id', '?')
        
        # Compressed content preview
        if len(content) <= max_length:
            preview = content if content else '(empty)'
        else:
            preview = f"{content[:max_length//2]}\n[...{len(content)-max_length} chars...]\n{content[-max_length//2:]}"
        
        docs.append(f"Doc: {name} (id:{doc_id})\n{preview}\n---")
    
    return "\n".join(docs)


def build_conversation_context(
    chat_history: List[Dict],
    window: int = 20,
    include_original_intent: bool = True
) -> str:
    """
    Build conversation context from history.
    
    Args:
        chat_history: List of message dictionaries
        window: Number of recent messages to include
        include_original_intent: Whether to search for original intent in full history
    
    Returns:
        Formatted conversation context string
    """
    if not chat_history:
        return "No previous messages"
    
    # Use recent messages
    recent_messages = chat_history[-window:]
    
    # Search for original intent in full history if requested
    original_intent_message = None
    if include_original_intent:
        for msg in reversed(chat_history):
            role = msg.get("role", "user")
            if hasattr(role, 'value'):
                role = role.value
            elif not isinstance(role, str):
                role = str(role).lower()
            
            if role == "user" or role == "USER":
                content = msg.get("content", "")
                content_lower = content.lower()
                
                if any(word in content_lower for word in ["create", "make a new", "write a", "new document"]):
                    original_intent_message = msg
                    break
                elif any(word in content_lower for word in ["edit", "add", "update", "change", "save"]):
                    original_intent_message = msg
                    break
    
    context_lines = []
    
    # Include original intent message if found and not already in recent
    if original_intent_message:
        original_in_recent = any(
            msg.get("content") == original_intent_message.get("content")
            for msg in recent_messages
        )
        
        if not original_in_recent:
            content = original_intent_message.get("content", "")
            original_index = next(
                (i for i, msg in enumerate(chat_history) if msg == original_intent_message),
                -1
            )
            messages_ago = len(chat_history) - original_index if original_index >= 0 else "unknown"
            context_lines.append(f"user: {content} (previous request - {messages_ago} messages ago, for context only)")
            context_lines.append("...")
    
    # Include recent messages
    for msg in recent_messages:
        role = msg.get("role", "user")
        if hasattr(role, 'value'):
            role = role.value
        elif not isinstance(role, str):
            role = str(role).lower()
        content = msg.get("content", "")
        
        # Include pending confirmation context if present
        if msg.get("pending_confirmation"):
            intent = msg.get("intent_statement", "")
            context_lines.append(f"{role}: {content} [PENDING CONFIRMATION: {intent}]")
        else:
            context_lines.append(f"{role}: {content}")
    
    return "\n".join(context_lines)
