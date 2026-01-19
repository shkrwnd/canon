"""
Routers - Strategy pattern for routing to templates.

- TemplateRouter: Routes to different prompt templates based on use case
Note: Intent classification (Stage 1) directly uses IntentClassificationTemplate
"""

from typing import Optional
from .templates import (
    PromptTemplate,
    AgentDecisionTemplate,
    DocumentRewriteTemplate,
    ConversationalTemplate
)


class TemplateRouter:
    """
    Router for selecting appropriate prompt templates.
    
    Routes to different template types based on use case (agent decision,
    document rewrite, conversational). Follows the Strategy pattern to
    decouple template selection logic from prompt generation.
    """
    
    def route_agent_decision(
        self,
        intent_type: str
    ) -> AgentDecisionTemplate:
        """
        Route to agent decision template based on intent type.
        
        Args:
            intent_type: "conversation", "edit", "create", or "clarify"
        
        Returns:
            AgentDecisionTemplate instance
        """
        return AgentDecisionTemplate(intent_type=intent_type)
    
    def route_document_rewrite(
        self,
        edit_scope: Optional[str] = None
    ) -> DocumentRewriteTemplate:
        """
        Route to document rewrite template.
        
        Args:
            edit_scope: "selective" or "full" or None
        
        Returns:
            DocumentRewriteTemplate instance
        """
        return DocumentRewriteTemplate(edit_scope=edit_scope)
    
    def route_conversational(
        self,
        has_web_search: bool = False
    ) -> ConversationalTemplate:
        """
        Route to conversational template.
        
        Args:
            has_web_search: Whether web search results are available
        
        Returns:
            ConversationalTemplate instance
        """
        return ConversationalTemplate(has_web_search=has_web_search)
