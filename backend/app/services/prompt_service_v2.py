"""
Prompt Service V2 - New modular prompt architecture.

This service uses the new prompt architecture (Policy Pack, Templates, Builder, Router)
while maintaining the same interface as the original PromptService for easy migration.
"""

from typing import Dict, Any, Optional, List
import logging

from .prompts import (
    create_agent_policy_pack,
    PromptBuilder,
    TemplateRouter,
    IntentClassificationTemplate,
)

logger = logging.getLogger(__name__)


class PromptServiceV2:
    """
    New prompt service using the modular architecture.
    
    This service maintains the same interface as PromptService for backward compatibility,
    but uses the new Policy Pack, Templates, Builder, and Router patterns internally.
    """
    
    def __init__(self):
        """Initialize the prompt service with policy pack and router."""
        self.policy = create_agent_policy_pack()
        self.template_router = TemplateRouter()  # For general template routing
        logger.debug("Initialized PromptServiceV2 with new modular architecture")
    
    def classify_intent(
        self,
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate intent classification prompt.
        
        Args:
            user_message: User's message
            documents: List of document dictionaries
            project_context: Optional project context (id, name, description)
            chat_history: Optional chat history for context
        
        Returns:
            Intent classification prompt string
        """
        from ..config import settings
        prompt_version = getattr(settings, 'intent_classification_prompt_version', 'contextual')
        
        # Stage 1: Intent Classification (directly use IntentClassificationTemplate)
        template = IntentClassificationTemplate(prompt_version=prompt_version)
        
        # Only include sections relevant to intent classification
        # This reduces prompt size significantly (~60-70% reduction) and improves focus
        prompt = (PromptBuilder(
            policy=self.policy,
            template=template,
            runtime={"user_message": user_message}
        )
        .with_documents(documents)
        .with_project_context(project_context or {})
        .with_chat_history(chat_history or [])
        .with_sections([
            "role",           # Agent identity
            "objective",      # What agent does
            "constraints",    # Key constraints
            "intent"          # Intent classification rules, action types, edge cases, confidence
            # Excluded: documents, web_search, conversation, process, output_format
            # These are not needed for Stage 1 classification
        ])
        .build())
        
        logger.debug(f"Generated intent classification prompt (version: {prompt_version})")
        return prompt
    
    def get_agent_decision_prompt(
        self,
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        intent_type: Optional[str] = None,
        intent_metadata: Optional[Dict] = None
    ) -> str:
        """
        Generate agent decision prompt.
        
        Args:
            user_message: User's message
            documents: List of document dictionaries
            project_context: Optional project context (id, name, description)
            intent_type: Intent type from Stage 1 ("conversation", "edit", "create", "clarify")
            intent_metadata: Optional intent metadata from Stage 1
        
        Returns:
            Agent decision prompt string
        """
        template = self.template_router.route_agent_decision(intent_type or "conversation")
        
        # Get examples if available
        examples = None
        try:
            from ..prompts.examples import PROMPT_EXAMPLES
            if PROMPT_EXAMPLES:
                examples = PROMPT_EXAMPLES[:2000]
        except ImportError:
            logger.debug("Could not load prompt examples")
        
        # Only include sections relevant to agent decision (Stage 2)
        # This reduces prompt size significantly (~50-60% reduction) and improves focus
        # Exclude intent classification rules (already done in Stage 1)
        prompt = (PromptBuilder(
            policy=self.policy,
            template=template,
            runtime={"user_message": user_message}
        )
        .with_documents(documents)
        .with_project_context(project_context or {})
        .with_intent_metadata(intent_metadata or {})
        .with_examples(examples)
        .with_sections([
            "role",           # Agent identity
            "objective",      # What agent does
            "constraints",    # Key constraints
            "documents",      # Document resolution, edit rules, create rules, content alignment
            "web_search",     # Web search triggers, query generation, attribution
            "conversation",   # Conversation rules (for conversational responses)
            "safety",         # Safety rules
            "validation",     # Validation rules
            "output_format"   # Required for JSON response
            # Excluded: intent (already classified in Stage 1)
        ])
        .build())
        
        logger.debug(f"Generated agent decision prompt (intent_type: {intent_type})")
        return prompt
    
    def get_document_rewrite_prompt(
        self,
        user_message: str,
        standing_instruction: str,
        current_content: str,
        web_search_results: Optional[str] = None,
        edit_scope: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        intent_statement: Optional[str] = None
    ) -> str:
        """
        Generate document rewrite prompt.
        
        Args:
            user_message: User's edit request
            standing_instruction: Document's standing instruction
            current_content: Current document content
            web_search_results: Optional web search results
            edit_scope: Optional edit scope ("selective" or "full")
            validation_errors: Optional list of validation errors from previous attempt
            intent_statement: Optional intent statement
        
        Returns:
            Document rewrite prompt string
        """
        template = self.template_router.route_document_rewrite(edit_scope=edit_scope)
        
        prompt = (PromptBuilder(
            policy=self.policy,
            template=template,
            runtime={
                "user_message": user_message,
                "standing_instruction": standing_instruction,
                "current_content": current_content,
                "web_search_results": web_search_results,
                "validation_errors": validation_errors,
                "intent_statement": intent_statement
            }
        ).build())
        
        logger.debug(f"Generated document rewrite prompt (edit_scope: {edit_scope})")
        return prompt
    
    def get_conversational_prompt(
        self,
        user_message: str,
        context: str = "",
        web_search_results: Optional[str] = None
    ) -> str:
        """
        Generate conversational prompt.
        
        Args:
            user_message: User's message
            context: Optional context string
            web_search_results: Optional web search results to include in response
        
        Returns:
            Conversational prompt string
        """
        template = self.template_router.route_conversational(has_web_search=web_search_results is not None)
        
        # Filter sections: exclude OUTPUT FORMAT (it's for agent decisions, not conversations)
        # Only include role, constraints, and conversation rules - no JSON output format
        prompt = (PromptBuilder(
            policy=self.policy,
            template=template,
            runtime={
                "user_message": user_message,
                "context": context,
                "web_search_results": web_search_results
            }
        )
        .with_sections(["role", "constraints", "conversation"])  # Exclude output_format
        .build())
        
        logger.debug(f"Generated conversational prompt (has_web_search: {web_search_results is not None})")
        return prompt
