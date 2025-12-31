"""
Intent Validator - LLM-based validation of document changes against user intent.

This module provides intent validation to determine if document changes
(section removals, structural changes, content reductions) match what
the user explicitly requested.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import logging
from ..core.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


@dataclass
class IntentValidationResult:
    """Result of intent validation"""
    all_changes_intentional: bool
    intentional_changes: List[Dict[str, Any]]
    unintentional_errors: List[str]
    reasoning: str


class IntentValidator:
    """
    Validates if document changes match user intent using LLM analysis.
    
    This service is decoupled from document validation and updater logic,
    focusing solely on intent analysis.
    """
    
    def __init__(self, llm_service):
        """
        Initialize intent validator with LLM service.
        
        Args:
            llm_service: LLMService instance for making LLM calls
        """
        self.llm_service = llm_service
        self.prompt_service = llm_service.prompt_service
    
    async def validate_changes_against_intent(
        self,
        user_message: str,
        validation_result: Any,  # ValidationResult from document_validator
        original_content: str,
        new_content: str
    ) -> IntentValidationResult:
        """
        Validate if document changes match user's explicit intent.
        
        Args:
            user_message: The user's original request
            validation_result: ValidationResult from DocumentValidator.validate_rewrite()
            original_content: Original document content
            new_content: New document content after rewrite
        
        Returns:
            IntentValidationResult indicating which changes are intentional
        """
        # Check if there are any errors that can be validated against intent
        if not validation_result.has_intent_checkable_errors():
            # No checkable errors - all errors are technical (markdown, placeholders, etc.)
            return IntentValidationResult(
                all_changes_intentional=False,
                intentional_changes=[],
                unintentional_errors=validation_result.errors,
                reasoning="No intent-checkable errors found. All errors are technical."
            )
        
        checkable_errors = validation_result.get_intent_checkable_errors()
        change_details = validation_result.change_details
        
        # Build comprehensive prompt for LLM analysis
        prompt = self._build_intent_validation_prompt(
            user_message=user_message,
            checkable_errors=checkable_errors,
            change_details=change_details
        )
        
        # Call LLM to analyze intent
        with tracer.start_as_current_span("intent_validator.validate_intent") as span:
            span.set_attribute("intent_validator.checkable_errors_count", len(checkable_errors))
            span.set_attribute("intent_validator.user_message_length", len(user_message))
            
            try:
                result = await self._call_llm_for_intent_analysis(prompt, span)
                span.set_attribute("intent_validator.all_intentional", result.all_changes_intentional)
                span.set_attribute("intent_validator.intentional_count", len(result.intentional_changes))
                return result
            except Exception as e:
                logger.error(f"Error during intent validation: {e}")
                span.record_exception(e)
                # On error, assume changes are not intentional (safety first)
                return IntentValidationResult(
                    all_changes_intentional=False,
                    intentional_changes=[],
                    unintentional_errors=validation_result.errors,
                    reasoning=f"Intent validation failed: {str(e)}. Assuming changes are not intentional."
                )
    
    def _build_intent_validation_prompt(
        self,
        user_message: str,
        checkable_errors: List[Dict[str, Any]],
        change_details: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM intent validation"""
        
        changes_summary = []
        for change in checkable_errors:
            change_type = change["type"]
            
            if change_type == "section_removal":
                missing_sections = change.get("missing_sections", [])
                changes_summary.append(
                    f"- **Removed sections**: {', '.join(missing_sections[:5])}"
                    + (f" and {len(missing_sections) - 5} more" if len(missing_sections) > 5 else "")
                )
            
            elif change_type == "structural_change":
                original_count = change.get("original_section_count", 0)
                new_count = change.get("new_section_count", 0)
                changes_summary.append(
                    f"- **Structure changed**: {original_count} sections → {new_count} sections "
                    f"({((new_count - original_count) / original_count * 100) if original_count > 0 else 0:.1f}% change)"
                )
            
            elif change_type == "content_reduction":
                original_len = change.get("original_length", 0)
                new_len = change.get("new_length", 0)
                reduction = change.get("reduction_pct", 0)
                changes_summary.append(
                    f"- **Content reduced**: {original_len:,} chars → {new_len:,} chars "
                    f"({reduction:.1f}% reduction)"
                )
        
        prompt = f"""Analyze if the changes made to the document align with what the user explicitly requested.

User's request: "{user_message}"

Changes detected in the rewritten document:
{chr(10).join(changes_summary)}

Document structure:
- Original: {change_details.get('original_section_count', 0)} sections, {change_details.get('original_length', 0):,} characters
- New: {change_details.get('new_section_count', 0)} sections, {change_details.get('new_length', 0):,} characters

Question: Do these changes match what the user asked for?

Consider:
1. **Removals**: Did user explicitly ask to remove sections? 
   - Direct: "remove X", "delete Y section", "drop Z", "eliminate W"
   - Indirect: "without the tokens section", "simplify by removing technical parts"
   - Context: "make it shorter" might mean removing sections, but be cautious

2. **Rewrites/Restructuring**: Did user ask to rewrite or reorganize?
   - "rewrite the document", "restructure", "reorganize", "complete overhaul"
   - "better organization" might involve structural changes
   - "simplify" might involve removing sections or restructuring

3. **Content Reduction**: Did user ask to make it shorter/more concise?
   - "make it shorter", "more concise", "condense", "simplify"
   - "remove unnecessary parts" might mean significant reduction
   - "cut down" or "trim" suggests reduction is intentional

4. **Safety First**: 
   - If unclear or ambiguous, assume NOT intentional (better to preserve content)
   - Only mark as intentional if user's request clearly indicates the change
   - Partial matches (e.g., "shorter" but not "remove sections") should be cautious

Respond with JSON:
{{
    "all_changes_intentional": boolean,  // True if ALL changes match user intent
    "intentional_changes": [
        {{
            "type": "section_removal" | "structural_change" | "content_reduction",
            "description": "What change was intentional",
            "user_intent": "How user's request matches this change"
        }}
    ],
    "unintentional_errors": [
        "error message 1",  // Errors that don't match user intent
        "error message 2"
    ],
    "reasoning": "Brief explanation of your analysis"
}}"""
        
        return prompt
    
    async def _call_llm_for_intent_analysis(
        self,
        prompt: str,
        span: Any
    ) -> IntentValidationResult:
        """Call LLM to analyze intent"""
        
        model = self.llm_service.provider.get_default_model()
        provider_name = self.llm_service.provider.__class__.__name__
        response_format = (
            {"type": "json_object"} 
            if self.llm_service.provider.supports_json_mode() 
            else None
        )
        
        span.set_attribute("intent_validator.model", model)
        span.set_attribute("intent_validator.provider", provider_name)
        
        messages = [
            {
                "role": "system",
                "content": "Analyze if document changes match user intent. Respond with valid JSON only."
            },
            {"role": "user", "content": prompt}
        ]
        
        async with self.llm_service._semaphore:
            with tracer.start_as_current_span("intent_validator.llm_call") as api_span:
                api_span.set_attribute("llm.api.type", "chat_completion")
                api_span.set_attribute("llm.api.model", model)
                
                response_text = await self.llm_service.provider.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=0.3,  # Lower temperature for more consistent analysis
                    response_format=response_format
                )
                
                api_span.set_attribute("llm.response.length", len(response_text))
        
        # Parse LLM response
        try:
            result_data = json.loads(response_text)
            
            return IntentValidationResult(
                all_changes_intentional=result_data.get("all_changes_intentional", False),
                intentional_changes=result_data.get("intentional_changes", []),
                unintentional_errors=result_data.get("unintentional_errors", []),
                reasoning=result_data.get("reasoning", "")
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response for intent validation: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

