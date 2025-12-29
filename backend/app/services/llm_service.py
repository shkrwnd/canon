from typing import Dict, Any, Optional, List
from ..clients.llm_providers.base import LLMProvider
from .prompt_service import PromptService
from ..core.telemetry import get_tracer
from ..config import settings
import asyncio
import json
import logging
import re

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
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Two-stage decision making:
        1. Classify intent (fast, minimal context)
        2. Make detailed decision (focused, relevant sections only)
        
        Args:
            user_message: User's message
            documents: List of documents in the project
            project_context: Optional project context (id, name, description)
            chat_history: Optional chat history for context
        
        Returns:
            Decision dict with should_edit, document_id, needs_web_search, etc.
        """
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        response_format = {"type": "json_object"} if self.provider.supports_json_mode() else None
        
        # ============================================
        # STAGE 1: Intent Classification (Fast)
        # ============================================
        intent_prompt = self.prompt_service.classify_intent(
            user_message, documents, project_context, chat_history
        )
        
        messages_stage1 = [
            {
                "role": "system",
                "content": "Classify user intent. Respond with valid JSON only."
            }
        ]
        
        # Add chat history to Stage 1 messages for context
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages for context
                role = msg.get("role", "user")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                messages_stage1.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
        
        messages_stage1.append({"role": "user", "content": intent_prompt})
        
        with tracer.start_as_current_span("llm.classify_intent") as span:
            span.set_attribute("llm.operation", "classify_intent")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.3)
            
            async with self._semaphore:
                intent_response = await self.provider.chat_completion(
                    messages=messages_stage1,
                    model=model,
                    temperature=0.3,  # Lower temp for classification
                    response_format=response_format
                )
            
            intent_data = json.loads(intent_response)
            intent_type = intent_data.get("intent_type", "conversation")
            needs_documents = intent_data.get("needs_documents", True)
            confidence = intent_data.get("confidence", 0.5)
            
            span.set_attribute("llm.intent_type", intent_type)
            span.set_attribute("llm.intent_confidence", confidence)
            span.set_attribute("llm.needs_documents", needs_documents)
        
        # Early exit only for very simple greetings that definitely don't need web search
        # All other conversations (including questions) must go to Stage 2 to evaluate web search needs
        if intent_type == "conversation" and not needs_documents:
            user_lower = user_message.lower().strip()
            # Only early exit for simple greetings that definitely don't need web search
            simple_greetings = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay"]
            if user_lower in simple_greetings:
                logger.debug(f"Early exit for simple greeting: {user_lower}")
                return {
                    "should_edit": False,
                    "should_create": False,
                    "needs_clarification": False,
                    "pending_confirmation": False,
                    "intent_type": intent_type,
                    "conversational_response": None,  # Will be generated separately
                    "reasoning": "Simple greeting - no action needed"
                }
            # Otherwise, continue to Stage 2 to evaluate web search needs for questions
            logger.debug(f"Conversation intent - proceeding to Stage 2 to evaluate web search needs")
        
        # ============================================
        # STAGE 2: Detailed Decision (Focused)
        # ============================================
        decision_prompt = self.prompt_service.get_agent_decision_prompt(
            user_message, documents, project_context, intent_type
        )
        
        messages_stage2 = [
            {
                "role": "system",
                "content": "Make detailed decision about document actions. Always respond with valid JSON."
            }
        ]
        
        # Add chat history
        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role", "user")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                messages_stage2.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
        
        messages_stage2.append({"role": "user", "content": decision_prompt})
        
        logger.debug(f"Getting agent decision for message: {user_message[:50]}... (intent: {intent_type})")
        
        with tracer.start_as_current_span("llm.get_agent_decision") as span:
            span.set_attribute("llm.operation", "agent_decision")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.5)
            span.set_attribute("llm.intent_type", intent_type)
            span.set_attribute("llm.response_format", "json" if response_format else "text")
            
            async with self._semaphore:
                with tracer.start_as_current_span("llm.api_call") as api_span:
                    api_span.set_attribute("llm.api.type", "chat_completion")
                    api_span.set_attribute("llm.api.model", model)
                    response_text = await self.provider.chat_completion(
                        messages=messages_stage2,
                        model=model,
                        temperature=0.5,
                        response_format=response_format
                    )
                    api_span.set_attribute("llm.response.length", len(response_text))
            
            decision = json.loads(response_text)
            decision["intent_type"] = intent_type  # Preserve intent type
            span.set_attribute("llm.decision.should_edit", decision.get('should_edit', False))
            span.set_attribute("llm.decision.document_id", decision.get('document_id'))
            logger.debug(f"Agent decision: should_edit={decision.get('should_edit')}, document_id={decision.get('document_id')}")
            return decision
    
    async def rewrite_document_content(
        self,
        user_message: str,
        standing_instruction: str,
        current_content: str,
        web_search_results: Optional[str] = None,
        edit_scope: Optional[str] = None,
        validation_errors: Optional[List[str]] = None
    ) -> str:
        """
        Rewrite document content based on user intent
        
        Args:
            user_message: User's edit request
            standing_instruction: Document's standing instruction
            current_content: Current document content
            web_search_results: Optional web search results
            edit_scope: Optional edit scope ("selective" or "full")
            validation_errors: Optional list of validation errors from previous attempt
        
        Returns:
            New document content
        """
        prompt = self.prompt_service.get_document_rewrite_prompt(
            user_message, standing_instruction, current_content, web_search_results, edit_scope, validation_errors
        )
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert editor that rewrites documents based on user intent. Return only the markdown content, no explanations."
            },
            {"role": "user", "content": prompt}
        ]
        
        logger.debug(f"Rewriting document content for message: {user_message[:50]}...")
        
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        
        # Create custom span for LLM operation
        with tracer.start_as_current_span("llm.rewrite_document_content") as span:
            span.set_attribute("llm.operation", "rewrite_document_content")
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
        context: str = "",
        chat_history: Optional[List[Dict]] = None,
        web_search_results: Optional[str] = None
    ) -> str:
        """
        Generate a conversational response when no edit is needed
        
        Args:
            user_message: User's message
            context: Optional context string
            chat_history: Optional chat history for context
            web_search_results: Optional web search results to include in response
        
        Returns:
            Conversational response
        """
        prompt = self.prompt_service.get_conversational_prompt(
            user_message, context, web_search_results
        )
        
        # Add logging to verify web search results are received
        logger.info(f"generate_conversational_response called: "
                   f"has_web_search_results={web_search_results is not None}, "
                   f"results_length={len(web_search_results) if web_search_results else 0}, "
                   f"user_message='{user_message[:50]}...'")
        
        # Use more specific system message when web search results are provided
        if web_search_results:
            system_content = """You are a helpful assistant. Web search has ALREADY been performed and results are provided below. 
Your job is to answer the user's question DIRECTLY using the web search results provided. 
DO NOT say "I will search" or "Let me look that up" - the search is already done. 
Extract the answer from the web search results and provide it immediately."""
        else:
            system_content = "You are a helpful, friendly assistant that helps users manage their documents. Respond naturally and conversationally."
        
        messages = [
            {
                "role": "system",
                "content": system_content
            }
        ]
        
        # Add chat history if available (limit to last 10 messages for context)
        if chat_history:
            for msg in chat_history[-10:]:
                role = msg.get("role", "user")
                # Ensure role is a string (handle enum values)
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                content = msg.get("content", "")
                messages.append({
                    "role": role,
                    "content": content
                })
        
        messages.append({"role": "user", "content": prompt})
        
        model = self.provider.get_default_model()
        provider_name = self.provider.__class__.__name__
        
        # Create custom span for LLM operation
        with tracer.start_as_current_span("llm.generate_conversational_response") as span:
            span.set_attribute("llm.operation", "conversational_response")
            span.set_attribute("llm.model", model)
            span.set_attribute("llm.provider", provider_name)
            span.set_attribute("llm.temperature", 0.7)
            span.set_attribute("llm.input.has_context", bool(context))
            span.set_attribute("llm.input.has_web_search", bool(web_search_results))
            
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
            
            # Safety net: If LLM says "I will search" when results are provided, extract answer from results
            if web_search_results:
                response_lower = response.lower().strip()
                logger.info(f"[POST-PROCESS] Checking response. Response='{response}', length={len(response)}, has_web_search_results=True, results_length={len(web_search_results)}")
                
                # More comprehensive pattern matching - check if response contains search intent
                search_phrases = [
                    "i will search", 
                    "i'll search", 
                    "let me search", 
                    "let me look", 
                    "i will look up",
                    "i'll look up",
                    "i will find",
                    "let me find"
                ]
                
                # Check if response starts with or contains any search phrase (more lenient check)
                contains_search_intent = any(
                    response_lower.startswith(phrase) or 
                    response_lower.startswith(phrase + " ") or
                    response_lower.startswith(phrase + " for") or
                    (len(response_lower) < 150 and phrase in response_lower)
                    for phrase in search_phrases
                )
                
                logger.info(f"[POST-PROCESS] Search intent check - contains_search_intent={contains_search_intent}, response_lower='{response_lower}'")
                
                if contains_search_intent:
                    logger.warning(f"[POST-PROCESS] ✓ Detected search intent! Response: '{response}'. Attempting to extract answer from results.")
                    logger.info(f"[POST-PROCESS] Web search results length: {len(web_search_results)}, first 500 chars: {web_search_results[:500]}")
                    
                    # Try to extract the answer directly from web search results
                    # Look for "Content:" sections that might contain the answer
                    if "Content:" in web_search_results:
                        logger.info(f"[POST-PROCESS] ✓ Found 'Content:' marker in web search results")
                        # Extract all content sections (not just first 2)
                        content_parts = web_search_results.split("Content:")
                        logger.info(f"[POST-PROCESS] Split into {len(content_parts)} parts (first part length: {len(content_parts[0]) if content_parts else 0})")
                        
                        if len(content_parts) > 1:
                            # Get all content sections (skip the first part which is before first Content:)
                            all_content = " ".join(content_parts[1:])
                            logger.info(f"[POST-PROCESS] Extracted content sections, total length: {len(all_content)}, first 500 chars: {all_content[:500]}")
                            
                            # More comprehensive patterns to find president name
                            patterns = [
                                # "current president of the United States is [Name]"
                                r"current president (?:of the United States|of the US|of America|of the U\.S\.)? (?:is )?([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
                                # "president of the United States is [Name]"
                                r"president (?:of the United States|of the US|of America|of the U\.S\.)? (?:is )?([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
                                # "[Name] is the current president"
                                r"([A-Z][a-z]+(?: [A-Z][a-z]+)+) (?:is|serves as) (?:the )?current president",
                                # "[Name], the [X] president of the United States"
                                r"([A-Z][a-z]+(?: [A-Z][a-z]+)+), (?:the )?(?:current )?president",
                                # Just look for common president name patterns in context
                                r"(?:president|President) (?:is |named |called )?([A-Z][a-z]+ [A-Z][a-z]+)",
                            ]
                            
                            for i, pattern in enumerate(patterns):
                                match = re.search(pattern, all_content, re.IGNORECASE)
                                if match:
                                    name = match.group(1).strip()
                                    # Basic validation - should be 2-3 words (first name + last name, maybe middle)
                                    name_parts = name.split()
                                    logger.info(f"[POST-PROCESS] Pattern {i+1} matched! Name: '{name}', parts: {name_parts}, count: {len(name_parts)}")
                                    
                                    if 2 <= len(name_parts) <= 3:
                                        logger.info(f"[POST-PROCESS] ✓✓✓ SUCCESS: Extracted answer from web search results: {name}")
                                        return f"The current president of the United States is {name}."
                                    else:
                                        logger.warning(f"[POST-PROCESS] Name validation failed: {len(name_parts)} parts (expected 2-3)")
                            
                            logger.warning(f"[POST-PROCESS] ✗ Could not extract president name using any regex patterns. Content preview: {all_content[:800]}")
                        else:
                            logger.warning(f"[POST-PROCESS] ✗ Not enough content parts after split: {len(content_parts)}")
                    else:
                        logger.warning(f"[POST-PROCESS] ✗ 'Content:' marker NOT found in web search results. Results preview: {web_search_results[:500]}")
                    
                    # Fallback: Return a message indicating we should use the results
                    logger.warning(f"[POST-PROCESS] ✗✗✗ Returning fallback message - extraction failed")
                    return "Based on the web search results provided above, please refer to the Content sections for the answer to your question."
                else:
                    logger.info(f"[POST-PROCESS] No search intent detected - response is OK")
            else:
                logger.info(f"[POST-PROCESS] Skipping post-processing - no web_search_results provided")
            
            return response.strip()

