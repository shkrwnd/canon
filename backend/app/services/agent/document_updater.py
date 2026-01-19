"""
Document Updater

Handles document update operations with validation and retry logic.
"""
from typing import Dict, Any, Optional
from opentelemetry import trace
from ...core.events import event_bus, DocumentUpdatedEvent
from ...core.telemetry import get_tracer
from ..document_validator import DocumentValidator, ValidationResult
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DocumentUpdater:
    """Handles document update operations with validation and retry logic"""
    
    def __init__(self, document_repo, llm_service, db, web_search_results=None, intent_validator=None):
        """
        Initialize document updater.
        
        Args:
            document_repo: Document repository
            llm_service: LLM service for rewriting
            db: Database session
            web_search_results: Optional web search results
            intent_validator: Optional IntentValidator for intent-based validation
        """
        self.document_repo = document_repo
        self.llm_service = llm_service
        self.db = db
        self.web_search_results = web_search_results
        self.intent_validator = intent_validator  # Optional, decoupled dependency
    
    async def update_document(
        self,
        decision: Dict[str, Any],
        user_id: int,
        user_message: str,
        target_document_id: int,
        span: trace.Span
    ) -> Optional[Dict[str, Any]]:
        """
        Update document with validation and retry logic.
        Returns: Updated document dict or None if update failed
        """
        target_document = self.document_repo.get_by_user_and_id(user_id, target_document_id)
        if not target_document:
            return None
        
        logger.info(f"Rewriting document {target_document_id}")
        edit_scope = decision.get("edit_scope")
        logger.debug(f"Edit scope: {edit_scope}")
        
        # Rewrite the document content
        new_content = await self.llm_service.rewrite_document_content(
            user_message=user_message,
            standing_instruction=target_document.standing_instruction,
            current_content=target_document.content,
            web_search_results=self.web_search_results,
            edit_scope=edit_scope,
            intent_statement=decision.get("intent_statement")
        )
        
        # Validate and update (handles retry logic)
        return await self._validate_and_update(
            target_document,
            new_content,
            user_message,
            edit_scope,
            user_id,
            target_document_id,
            decision,
            span
        )
    
    async def _validate_and_update(
        self,
        target_document,
        new_content: str,
        user_message: str,
        edit_scope: Optional[str],
        user_id: int,
        target_document_id: int,
        decision: Dict[str, Any],
        span: trace.Span
    ) -> Optional[Dict[str, Any]]:
        """Validate content and update document, with intent-aware retry logic"""
        # Step 1: Structural validation
        validation_result = DocumentValidator.validate_rewrite(
            new_content=new_content,
            original_content=target_document.content
        )
        
        # Step 2: If validation fails, check if changes match user intent (if intent validator available)
        if not validation_result.is_valid and self.intent_validator:
            # Check if there are intent-checkable errors
            if validation_result.has_intent_checkable_errors():
                logger.info("Validation failed with intent-checkable errors. Checking user intent...")
                span.set_attribute("agent.intent_validation_attempted", True)
                
                try:
                    intent_result = await self.intent_validator.validate_changes_against_intent(
                        user_message=user_message,
                        validation_result=validation_result,
                        original_content=target_document.content,
                        new_content=new_content,
                        intent_statement=decision.get("intent_statement"),
                        original_errors=validation_result.errors
                    )
                    
                    span.set_attribute("agent.intent_all_intentional", intent_result.all_changes_intentional)
                    span.set_attribute("agent.intent_intentional_count", len(intent_result.intentional_changes))
                    
                    # If all changes are intentional, allow update
                    if intent_result.all_changes_intentional:
                        logger.info(
                            f"All changes confirmed as intentional: {intent_result.reasoning}. "
                            f"Allowing update without retry."
                        )
                        # Clear intentional errors, keep only unintentional ones
                        validation_result.errors = intent_result.unintentional_errors
                        # Also keep technical errors (markdown, placeholders) that can't be intentional
                        technical_errors = [
                            err for err in validation_result.errors 
                            if "markdown" in err.lower() or "placeholder" in err.lower()
                        ]
                        validation_result.errors = technical_errors + intent_result.unintentional_errors
                        
                        # If no remaining errors, validation passes
                        if not validation_result.errors:
                            validation_result.is_valid = True
                            logger.info("Intent validation passed. Proceeding with update.")
                            # Store intent validation info in decision
                            decision['intent_validation'] = {
                                'all_intentional': True,
                                'intentional_changes': intent_result.intentional_changes,
                                'reasoning': intent_result.reasoning
                            }
                            # Proceed with update
                            return self._perform_update(
                                target_document_id,
                                new_content,
                                validation_result,
                                user_id,
                                decision,
                                span
                            )
                        else:
                            logger.info(
                                f"Some errors remain after intent validation: {validation_result.errors}. "
                                f"Proceeding with retry."
                            )
                    else:
                        logger.info(
                            f"Changes don't fully match user intent. "
                            f"Intentional: {len(intent_result.intentional_changes)}, "
                            f"Unintentional: {len(intent_result.unintentional_errors)}. "
                            f"Proceeding with retry."
                        )
                        # Store intent validation info
                        decision['intent_validation'] = {
                            'all_intentional': False,
                            'intentional_changes': intent_result.intentional_changes,
                            'unintentional_errors': intent_result.unintentional_errors,
                            'reasoning': intent_result.reasoning
                        }
                        # Update validation_result.errors to only include unintentional errors
                        # This way the retry will focus on fixing only the unintentional removals
                        validation_result.errors = intent_result.unintentional_errors
                        logger.info(
                            f"Updated validation errors to only unintentional ones: {len(validation_result.errors)} errors"
                        )
                
                except Exception as e:
                    logger.error(f"Error during intent validation: {e}. Proceeding with standard retry.")
                    span.record_exception(e)
                    # On error, fall through to standard retry logic
        
        # Step 3: If validation still fails, retry once
        if not validation_result.is_valid:
            logger.warning(
                f"Document rewrite validation failed: {validation_result.errors}. Retrying once..."
            )
            span.set_attribute("agent.validation_failed", True)
            span.set_attribute("agent.validation_errors", str(validation_result.errors))
            
            # Retry rewrite with validation errors included and force selective scope
            retry_edit_scope = "selective" if edit_scope == "full" else edit_scope
            logger.debug(f"Retrying with edit_scope: {retry_edit_scope} (was {edit_scope})")
            
            new_content = await self.llm_service.rewrite_document_content(
                user_message=user_message,
                standing_instruction=target_document.standing_instruction,
                current_content=target_document.content,
                web_search_results=self.web_search_results,
                edit_scope=retry_edit_scope,
                validation_errors=validation_result.errors,
                intent_statement=decision.get("intent_statement")
            )
            
            # Validate again
            validation_result = DocumentValidator.validate_rewrite(
                new_content=new_content,
                original_content=target_document.content
            )
            
            if not validation_result.is_valid:
                # Still failing - DO NOT UPDATE
                error_msg = f"Document rewrite failed validation after retry: {', '.join(validation_result.errors)}"
                logger.error(error_msg)
                span.record_exception(Exception(error_msg))
                decision['validation_errors'] = validation_result.errors
                decision['validation_warnings'] = validation_result.warnings
                logger.warning(f"Skipping document update for document {target_document_id} due to validation failure")
                span.set_attribute("agent.document_updated", False)
                return None
        
        # Validation passed (either first try or after retry)
        # Log warnings even if validation passed
        if validation_result.warnings:
            logger.info(f"Document rewrite validation warnings: {validation_result.warnings}")
            decision['validation_warnings'] = validation_result.warnings
        
        # Update document using repository
        return self._perform_update(
            target_document_id,
            new_content,
            validation_result,
            user_id,
            decision,
            span
        )
    
    def _perform_update(
        self,
        target_document_id: int,
        new_content: str,
        validation_result: ValidationResult,
        user_id: int,
        decision: Dict[str, Any],
        span: trace.Span
    ) -> Optional[Dict[str, Any]]:
        """Perform the actual document update"""
        with tracer.start_as_current_span("agent.update_document") as db_span:
            db_span.set_attribute("db.operation", "update_document")
            db_span.set_attribute("db.document_id", target_document_id)
            db_span.set_attribute("db.validation_passed", validation_result.is_valid)
            updated_document_obj = self.document_repo.update(
                target_document_id,
                content=new_content
            )
            
            if updated_document_obj:
                # Commit the transaction
                self.document_repo.commit()
                self.db.refresh(updated_document_obj)
                
                updated_document = {
                    "id": updated_document_obj.id,
                    "name": updated_document_obj.name,
                    "standing_instruction": updated_document_obj.standing_instruction,
                    "content": updated_document_obj.content,
                    "project_id": updated_document_obj.project_id,
                    "user_id": updated_document_obj.user_id,
                    "created_at": updated_document_obj.created_at,
                    "updated_at": updated_document_obj.updated_at
                }
                logger.info(f"Document {target_document_id} updated successfully")
                db_span.set_attribute("db.update_success", True)
                span.set_attribute("agent.document_updated", True)
                
                # Publish document updated event
                event_bus.publish(DocumentUpdatedEvent(
                    document_id=target_document_id,
                    project_id=updated_document_obj.project_id,
                    user_id=user_id,
                    changes={"content": "updated"}
                ))
                return updated_document
            else:
                db_span.set_attribute("db.update_success", False)
                span.set_attribute("agent.document_updated", False)
                return None

