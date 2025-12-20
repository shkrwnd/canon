from typing import Dict, Any, Optional
from ..clients.llm_providers.base import LLMProvider
from .prompt_service import PromptService
from ..core.telemetry import get_tracer
from ..config import settings
import asyncio
import json
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class LLMService:
    """High-level service for LLM operations"""
    
    def __init__(self, provider: LLMProvider, max_concurrent_requests: Optional[int] = None):
        """
        Initialize LLM service with a provider
        
        Args:
            provider: LLM provider implementation
            max_concurrent_requests: Maximum concurrent API requests (defaults to settings)
        """
        self.provider = provider
        self.prompt_service = PromptService()
        
        # Semaphore for rate limiting
        max_concurrent = max_concurrent_requests or getattr(
            settings, 'llm_max_concurrent_requests', 10
        )
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.debug(
            f"Initialized LLMService with provider: {provider.__class__.__name__}, "
            f"max_concurrent={max_concurrent}"
        )
    
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
        
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        
        # Create custom span for LLM operation
        with tracer.start_as_current_span("llm.get_agent_decision") as span:
            span.set_attribute("llm.operation", "agent_decision")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.5)
            span.set_attribute("llm.response_format", "json" if response_format else "text")
            
            # Rate limit with semaphore
            async with self._semaphore:
                with tracer.start_as_current_span("llm.api_call") as api_span:
                    api_span.set_attribute("llm.api.type", "chat_completion")
                    api_span.set_attribute("llm.api.model", model)
                    response_text = await self.provider.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=0.5,
                        response_format=response_format
                    )
                    api_span.set_attribute("llm.response.length", len(response_text))
            
            decision = json.loads(response_text)
            span.set_attribute("llm.decision.should_edit", decision.get('should_edit', False))
            span.set_attribute("llm.decision.module_id", decision.get('module_id'))
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
        
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        
        # Create custom span for LLM operation
        with tracer.start_as_current_span("llm.rewrite_module_content") as span:
            span.set_attribute("llm.operation", "rewrite_module_content")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.7)
            span.set_attribute("llm.input.content_length", len(current_content))
            span.set_attribute("llm.input.has_web_search", web_search_results is not None)
            
            # Rate limit with semaphore
            async with self._semaphore:
                with tracer.start_as_current_span("llm.api_call") as api_span:
                    api_span.set_attribute("llm.api.type", "chat_completion")
                    api_span.set_attribute("llm.api.model", model)
                    content = await self.provider.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=0.7
                    )
                    api_span.set_attribute("llm.response.length", len(content))
            
            span.set_attribute("llm.output.content_length", len(content))
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
        
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        
        # Create custom span for LLM operation
        with tracer.start_as_current_span("llm.generate_conversational_response") as span:
            span.set_attribute("llm.operation", "conversational_response")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.7)
            span.set_attribute("llm.input.has_context", bool(context))
            
            # Rate limit with semaphore
            async with self._semaphore:
                with tracer.start_as_current_span("llm.api_call") as api_span:
                    api_span.set_attribute("llm.api.type", "chat_completion")
                    api_span.set_attribute("llm.api.model", model)
                    response = await self.provider.chat_completion(
                        messages=messages,
                        model=model,
                        temperature=0.7
                    )
                    api_span.set_attribute("llm.response.length", len(response))
            
            span.set_attribute("llm.output.length", len(response))
            return response.strip()

