from typing import Dict, Any, Optional
from ..clients.providers.base import LLMProvider
from .prompt_service import PromptService
import json
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """High-level service for LLM operations"""
    
    def __init__(self, provider: LLMProvider):
        """
        Initialize LLM service with a provider
        
        Args:
            provider: LLM provider implementation
        """
        self.provider = provider
        self.prompt_service = PromptService()
        logger.debug(f"Initialized LLMService with provider: {provider.__class__.__name__}")
    
    async def get_agent_decision(
        self,
        user_message: str,
        modules: list,
        current_module: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get agent decision on what to do
        
        Args:
            user_message: User's message
            modules: List of user's modules
            current_module: Optional current module context
        
        Returns:
            Decision dict with should_edit, module_id, needs_web_search, etc.
        """
        # Generate prompt (business logic)
        prompt = self.prompt_service.get_agent_decision_prompt(
            user_message, modules, current_module
        )
        
        # Make API call (provider-specific)
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that helps users manage documents. You can have conversations and make decisions about editing. Always respond with valid JSON."
            },
            {"role": "user", "content": prompt}
        ]
        
        response_format = None
        if self.provider.supports_json_mode():
            response_format = {"type": "json_object"}
        
        logger.debug(f"Getting agent decision for message: {user_message[:50]}...")
        response_text = await self.provider.chat_completion(
            messages=messages,
            model=self.provider.get_default_model(),
            temperature=0.5,
            response_format=response_format
        )
        
        decision = json.loads(response_text)
        logger.debug(f"Agent decision: should_edit={decision.get('should_edit')}, module_id={decision.get('module_id')}")
        return decision
    
    async def rewrite_module_content(
        self,
        user_message: str,
        standing_instruction: str,
        current_content: str,
        web_search_results: Optional[str] = None
    ) -> str:
        """
        Rewrite module content based on user intent
        
        Args:
            user_message: User's edit request
            standing_instruction: Module's standing instruction
            current_content: Current module content
            web_search_results: Optional web search results
        
        Returns:
            New module content
        """
        prompt = self.prompt_service.get_module_rewrite_prompt(
            user_message, standing_instruction, current_content, web_search_results
        )
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert editor that rewrites documents based on user intent. Return only the markdown content, no explanations."
            },
            {"role": "user", "content": prompt}
        ]
        
        logger.debug(f"Rewriting module content for message: {user_message[:50]}...")
        content = await self.provider.chat_completion(
            messages=messages,
            model=self.provider.get_default_model(),
            temperature=0.7
        )
        
        logger.debug(f"Module content rewritten, length: {len(content)}")
        return content.strip()
    
    async def generate_conversational_response(
        self,
        user_message: str,
        context: str = ""
    ) -> str:
        """
        Generate a conversational response when no edit is needed
        
        Args:
            user_message: User's message
            context: Optional context string
        
        Returns:
            Conversational response
        """
        prompt = self.prompt_service.get_conversational_prompt(user_message, context)
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful, friendly assistant that helps users manage their documents. Respond naturally and conversationally."
            },
            {"role": "user", "content": prompt}
        ]
        
        response = await self.provider.chat_completion(
            messages=messages,
            model=self.provider.get_default_model(),
            temperature=0.7
        )
        
        return response.strip()

