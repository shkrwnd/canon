from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..repositories import DocumentRepository, ProjectRepository, ChatRepository
from ..models import Document, Project, ChatMessage, MessageRole
from ..schemas import AgentActionRequest, AgentActionResponse, ChatCreate, ChatMessageCreate, Document as DocumentSchema, DocumentCreate, ChatMessage as ChatMessageSchema
from ..exceptions import ValidationError
from ..core.events import event_bus, AgentActionCompletedEvent, DocumentUpdatedEvent
from ..core.telemetry import get_tracer
from opentelemetry import trace
from .llm_service import LLMService
from .chat_service import ChatService
from .document_service import DocumentService
from .document_validator import DocumentValidator, ValidationResult
from .web_search import WebSearchService
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class AgentService:
    """Service for agent operations"""
    
    def __init__(self, db: Session, llm_service: LLMService, document_service: DocumentService = None):
        """
        Initialize agent service
        
        Args:
            db: Database session
            llm_service: LLM service (required, injected via dependency injection)
            document_service: Document service (optional, for document creation)
        """
        self.document_repo = DocumentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.chat_repo = ChatRepository(db)
        self.db = db
        self.llm_service = llm_service
        self.web_search_service = WebSearchService(llm_service)
        self.document_service = document_service
    
    async def _get_or_create_chat(
        self,
        user_id: int,
        request: AgentActionRequest,
        chat_service: ChatService,
        span: trace.Span
    ):
        """
        Get existing chat or create new one.
        Extracted from process_agent_action_with_chat lines 550-589.
        """
        chat = None
        if request.chat_id:
            with tracer.start_as_current_span("agent.get_chat") as chat_span:
                chat_span.set_attribute("chat.operation", "get_chat")
                try:
                    chat = chat_service.get_chat(user_id, request.chat_id)
                    chat_span.set_attribute("chat.found", True)
                    # Validate that the chat belongs to the requested project (if project_id is provided)
                    if request.project_id and chat.project_id != request.project_id:
                        # Chat exists but belongs to a different project - create a new chat for this project
                        logger.info(f"Chat {request.chat_id} belongs to different project, creating new chat")
                        chat = None
                        chat_span.set_attribute("chat.project_mismatch", True)
                except Exception as e:
                    logger.warning(f"Failed to get chat {request.chat_id}: {e}")
                    chat_span.set_attribute("chat.found", False)
                    chat_span.record_exception(e)
                    chat = None
        
        if not chat:
            # Create new chat - use project_id from request
            project_id_to_use = request.project_id
            if not project_id_to_use:
                raise ValidationError("project_id is required to create a new chat")
            
            logger.info(f"Creating new chat for user {user_id}, project_id: {project_id_to_use}")
            with tracer.start_as_current_span("agent.create_chat") as chat_span:
                chat_span.set_attribute("chat.operation", "create_chat")
                chat_span.set_attribute("chat.project_id", project_id_to_use)
                chat = chat_service.create_chat(
                    user_id,
                    ChatCreate(project_id=project_id_to_use)
                )
                chat_span.set_attribute("chat.id", chat.id)
                span.set_attribute("agent.chat_created", True)
        else:
            span.set_attribute("agent.chat_created", False)
        
        span.set_attribute("agent.chat_id", chat.id)
        return chat
    
    def _store_user_message(
        self,
        user_id: int,
        chat_id: int,
        message: str,
        chat_service: ChatService
    ):
        """
        Store user message in chat.
        Extracted from process_agent_action_with_chat lines 591-605.
        """
        logger.debug(f"Storing user message in chat {chat_id}")
        with tracer.start_as_current_span("agent.store_user_message") as msg_span:
            msg_span.set_attribute("message.operation", "store_user_message")
            msg_span.set_attribute("message.chat_id", chat_id)
            user_message = chat_service.add_message(
                user_id,
                chat_id,
                ChatMessageCreate(
                    role=MessageRole.USER,
                    content=message,
                    metadata={}
                )
            )
            msg_span.set_attribute("message.id", user_message.id)
        return user_message
    
    def _build_chat_history(
        self,
        chat_service: ChatService,
        user_id: int,
        chat_id: int
    ) -> List[Dict]:
        """
        Build chat history for LLM context.
        Extracted from process_agent_action_with_chat lines 607-632.
        """
        chat_messages_db = chat_service.get_chat_messages(user_id, chat_id)
        # Filter out the user message we just added to avoid duplication
        chat_history_for_llm = []
        for msg in chat_messages_db[:-1]:  # Exclude the last message
            role = msg.role.value if hasattr(msg.role, 'value') else msg.role
            content = msg.content
            # Use message_metadata attribute (column name is "metadata" but attribute is "message_metadata")
            metadata = msg.message_metadata if msg.message_metadata else {}
            decision = metadata.get("decision", {}) if isinstance(metadata, dict) else {}
            
            # Include decision metadata in history for context
            history_item = {
                "role": role,
                "content": content
            }
            
            # Add context about pending confirmation if present
            if decision.get("pending_confirmation"):
                history_item["pending_confirmation"] = True
                history_item["intent_statement"] = decision.get("intent_statement", "")
                history_item["document_id"] = decision.get("document_id")
                history_item["should_edit"] = decision.get("should_edit", False)
                history_item["should_create"] = decision.get("should_create", False)
            
            chat_history_for_llm.append(history_item)
        
        return chat_history_for_llm
    
    def _get_project_context(
        self,
        user_id: int,
        project_id: Optional[int],
        span: trace.Span
    ):
        """
        Get project and documents list.
        Extracted from process_agent_action lines 61-88.
        Returns: (project, documents_list)
        """
        project = None
        documents_list = []
        
        if project_id:
            with tracer.start_as_current_span("agent.get_project") as db_span:
                db_span.set_attribute("db.operation", "get_project")
                project = self.project_repo.get_by_user_and_id(user_id, project_id)
                if project:
                    db_span.set_attribute("db.project_found", True)
                    span.set_attribute("agent.project_name", project.name)
                else:
                    db_span.set_attribute("db.project_found", False)
            
            if project:
                with tracer.start_as_current_span("agent.get_project_documents") as db_span:
                    db_span.set_attribute("db.operation", "get_project_documents")
                    project_documents = self.document_repo.get_by_project_id(project_id)
                    db_span.set_attribute("db.result_count", len(project_documents))
                documents_list = [
                    {
                        "id": d.id,
                        "name": d.name,
                        "standing_instruction": d.standing_instruction,
                        "content": d.content
                    }
                    for d in project_documents
                ]
        
        return project, documents_list
    
    async def _perform_web_search_if_needed(
        self,
        decision: Dict[str, Any],
        user_message: str,
        project: Optional[Project],
        span: trace.Span
    ):
        """
        Perform web search if decision indicates it's needed.
        Extracted from process_agent_action lines 119-160.
        Returns: WebSearchResult object or None
        """
        web_search_result_obj = None
        
        # Log web search trigger check
        needs_web_search = decision.get("needs_web_search", False)
        search_query = decision.get("search_query")
        logger.info(f"Web search check: needs_web_search={needs_web_search}, search_query={search_query}")
        if not needs_web_search:
            logger.info("Web search not triggered: needs_web_search is False or missing")
        elif not search_query:
            logger.info("Web search not triggered: search_query is missing or empty")
        else:
            logger.info(f"Web search will be performed with query: {search_query}")
        
        # Perform web search if needed (using WebSearchService for retry logic)
        if decision.get("needs_web_search") and decision.get("search_query"):
            logger.info(f"Performing web search: {decision['search_query']}")
            with tracer.start_as_current_span("agent.web_search") as web_span:
                web_span.set_attribute("web_search.query", decision["search_query"])
                
                # Use WebSearchService for search with retry logic
                web_search_result_obj = await self.web_search_service.search_with_retry(
                    initial_query=decision["search_query"],
                    user_message=user_message,
                    context=f"Project: {project.name if project else 'Unknown'}"
                )
                
                # Get final results (best quality or latest)
                web_search_results = web_search_result_obj.get_best_results()
                web_search_performed = len(web_search_result_obj.attempts) > 0
                
                web_span.set_attribute("web_search.results_count", len(web_search_results) if web_search_results else 0)
                web_span.set_attribute("web_search.attempts", len(web_search_result_obj.attempts))
                web_span.set_attribute("web_search.was_retried", web_search_result_obj.was_retried())
        else:
            logger.info("Web search skipped: needs_web_search=False or search_query missing")
        
        # Log web search status after check
        web_search_results = web_search_result_obj.get_best_results() if web_search_result_obj else None
        logger.info(f"Web search status: performed={web_search_result_obj is not None}, "
                    f"results_length={len(web_search_results) if web_search_results else 0}, "
                    f"attempts={len(web_search_result_obj.attempts) if web_search_result_obj else 0}")
        
        return web_search_result_obj
    
    def _build_response(
        self,
        result: Dict[str, Any],
        agent_message: Any,
        request: AgentActionRequest,
        chat: Any,
        user_id: int
    ) -> AgentActionResponse:
        """
        Build AgentActionResponse from result and agent message.
        Extracted from process_agent_action_with_chat lines 963-1000.
        """
        # Convert updated or created document to schema if exists
        updated_document_schema = None
        if result.get("updated_document"):
            updated_document_schema = DocumentSchema(**result["updated_document"])
        elif result.get("created_document"):
            updated_document_schema = DocumentSchema(**result["created_document"])
        
        # Publish event for cross-cutting concerns (analytics, monitoring)
        decision = result["decision"]
        event_bus.publish(AgentActionCompletedEvent(
            user_id=user_id,
            chat_id=chat.id,
            project_id=request.project_id or chat.project_id,
            document_id=request.document_id or (result.get("updated_document", {}).get("id") if result.get("updated_document") else None) or (result.get("created_document", {}).get("id") if result.get("created_document") else None),
            action_type="agent_action",
            success=result.get("updated_document") is not None or result.get("created_document") is not None,
            metadata={
                "should_edit": decision.get("should_edit", False),
                "should_create": decision.get("should_create", False),
                "needs_clarification": decision.get("needs_clarification", False),
                "pending_confirmation": decision.get("pending_confirmation", False),
                "web_search_performed": result.get("web_search_performed", False),
                "document_updated": result.get("updated_document") is not None,
                "document_created": result.get("created_document") is not None,
                "intent_statement": decision.get("intent_statement"),
                "change_summary": decision.get("change_summary"),
                "content_summary": decision.get("content_summary")
            }
        ))
        
        return AgentActionResponse(
            document=updated_document_schema,
            chat_message=ChatMessageSchema.model_validate(agent_message),
            agent_decision=result["decision"],
            web_search_performed=result.get("web_search_performed", False)
        )
    
    async def process_agent_action(
        self,
        user_id: int,
        user_message: str,
        project_id: Optional[int] = None,
        document_id: Optional[int] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process agent action: detect intent, decide on edits, perform web search if needed,
        and rewrite document content.
        """
        logger.info(f"Processing agent action for user {user_id}, project_id: {project_id}")
        
        with tracer.start_as_current_span("agent.process_agent_action") as span:
            span.set_attribute("agent.user_id", user_id)
            span.set_attribute("agent.project_id", project_id)
            span.set_attribute("agent.message_length", len(user_message))
            
            try:
                # Get project and all documents in it
                project, documents_list = self._get_project_context(user_id, project_id, span)
                
                # Get agent decision (pass project context)
                project_context = {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description
                } if project else None
                
                decision = await self.llm_service.get_agent_decision(
                    user_message, 
                    documents_list, 
                    project_context=project_context,
                    chat_history=chat_history
                )
                
                # Log decision details for debugging
                logger.info(f"Agent decision received: should_edit={decision.get('should_edit')}, "
                            f"should_create={decision.get('should_create')}, "
                            f"document_id={decision.get('document_id')}, "
                            f"needs_web_search={decision.get('needs_web_search')}, "
                            f"search_query={decision.get('search_query')}, "
                            f"intent_statement={decision.get('intent_statement')}, "
                            f"content_summary={'present' if decision.get('content_summary') else 'missing'}, "
                            f"change_summary={'present' if decision.get('change_summary') else 'missing'}")
                logger.debug(f"Full decision JSON: {decision}")
                
                span.set_attribute("agent.decision.should_edit", decision.get("should_edit", False))
                span.set_attribute("agent.decision.document_id", decision.get("document_id"))
                span.set_attribute("agent.decision.needs_web_search", decision.get("needs_web_search", False))
                
                # Perform web search if needed
                web_search_result_obj = await self._perform_web_search_if_needed(
                    decision, user_message, project, span
                )
                web_search_performed = web_search_result_obj is not None
                web_search_results = web_search_result_obj.get_best_results() if web_search_result_obj else None
                
                # Rewrite document if decision says so
                updated_document = None
                if decision.get("should_edit") and decision.get("document_id"):
                    target_document_id = decision["document_id"]
                    with tracer.start_as_current_span("agent.get_target_document") as db_span:
                        db_span.set_attribute("db.operation", "get_target_document")
                        target_document = self.document_repo.get_by_user_and_id(user_id, target_document_id)
                    
                    if target_document:
                        logger.info(f"Rewriting document {target_document_id}")
                        # Get edit_scope from decision to determine preservation strategy
                        edit_scope = decision.get("edit_scope")
                        logger.debug(f"Edit scope: {edit_scope}")
                        # Rewrite the document content with edit scope awareness
                        new_content = await self.llm_service.rewrite_document_content(
                            user_message=user_message,
                            standing_instruction=target_document.standing_instruction,
                            current_content=target_document.content,
                            web_search_results=web_search_results,
                            edit_scope=edit_scope
                        )
                        
                        # Validate the rewritten content
                        validation_result = DocumentValidator.validate_rewrite(
                            new_content=new_content,
                            original_content=target_document.content
                        )
                        
                        # If validation fails, retry once
                        if not validation_result.is_valid:
                            logger.warning(
                                f"Document rewrite validation failed: {validation_result.errors}. Retrying once..."
                            )
                            span.set_attribute("agent.validation_failed", True)
                            span.set_attribute("agent.validation_errors", str(validation_result.errors))
                            
                            # Retry rewrite with validation errors included and force selective scope
                            # If validation failed due to lost sections, use selective to preserve content
                            retry_edit_scope = "selective" if edit_scope == "full" else edit_scope
                            logger.debug(f"Retrying with edit_scope: {retry_edit_scope} (was {edit_scope})")
                            
                            new_content = await self.llm_service.rewrite_document_content(
                                user_message=user_message,
                                standing_instruction=target_document.standing_instruction,
                                current_content=target_document.content,
                                web_search_results=web_search_results,
                                edit_scope=retry_edit_scope,
                                validation_errors=validation_result.errors
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
                                # Store validation errors in decision for user feedback
                                decision['validation_errors'] = validation_result.errors
                                decision['validation_warnings'] = validation_result.warnings
                                # Skip update - validation failed
                                updated_document = None
                                logger.warning(f"Skipping document update for document {target_document_id} due to validation failure")
                                span.set_attribute("agent.document_updated", False)
                            else:
                                # Validation passed - proceed with update
                                # Log warnings even if validation passed
                                if validation_result.warnings:
                                    logger.info(f"Document rewrite validation warnings: {validation_result.warnings}")
                                    decision['validation_warnings'] = validation_result.warnings
                                
                                # Update document using repository
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
                                            changes={"content": "updated"}  # Content was updated
                                        ))
                                    else:
                                        db_span.set_attribute("db.update_success", False)
                                        span.set_attribute("agent.document_updated", False)
                        else:
                            # Validation passed on first try - proceed with update
                            # Log warnings even if validation passed
                            if validation_result.warnings:
                                logger.info(f"Document rewrite validation warnings: {validation_result.warnings}")
                                decision['validation_warnings'] = validation_result.warnings
                            
                            # Update document using repository
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
                                        changes={"content": "updated"}  # Content was updated
                                    ))
                                else:
                                    db_span.set_attribute("db.update_success", False)
                                    span.set_attribute("agent.document_updated", False)
                
                # Handle document creation if requested
                created_document = None
                if decision.get("should_create") and project_id:
                    # Priority 1: Use document_name from decision (most reliable - LLM should provide this)
                    document_name = decision.get("document_name")
                    
                    # Priority 2: Extract from intent_statement (more flexible than hardcoded keywords)
                    if not document_name:
                        intent = decision.get("intent_statement", "")
                        if intent:
                            intent_lower = intent.lower()
                            
                            # Pattern 1: "called X", "named X", "for X"
                            if "called" in intent_lower or "named" in intent_lower or "for" in intent_lower:
                                parts = intent.split()
                                for i, part in enumerate(parts):
                                    if part.lower() in ["called", "named", "for"] and i + 1 < len(parts):
                                        document_name = " ".join(parts[i+1:]).strip('"\'.,')
                                        # Remove common words like "document", "in", "this", "project"
                                        document_name = document_name.replace("document", "").replace("in", "").replace("this", "").replace("project", "").strip()
                                        if document_name:
                                            logger.info(f"Extracted document name '{document_name}' from intent_statement")
                                            break
                            
                            # Pattern 2: "create X" or "I'll create X"
                            if not document_name:
                                parts = intent.split()
                                for i, part in enumerate(parts):
                                    if part.lower() == "create" and i + 1 < len(parts):
                                        # Take the next 1-3 words as potential document name
                                        potential_name = " ".join(parts[i+1:i+4])
                                        # Clean up common words
                                        potential_name = potential_name.replace("document", "").replace("a", "").replace("new", "").replace("for", "").replace("in", "").replace("this", "").replace("project", "").strip()
                                        if potential_name and len(potential_name) > 1:
                                            document_name = potential_name
                                            logger.info(f"Extracted document name '{document_name}' from intent_statement (create pattern)")
                                            break
                    
                    # Priority 3: Extract from user message as last resort (simple noun extraction)
                    # This is a fallback when LLM doesn't provide document_name or intent_statement extraction fails
                    if not document_name:
                        # Simple approach: look for nouns after action words
                        user_words = user_message.split()
                        action_words = ["add", "create", "make", "new", "my"]
                        stop_words = ["my", "favorite", "the", "a", "an", "for", "to", "in", "with", "about"]
                        
                        for i, word in enumerate(user_words):
                            word_lower = word.lower()
                            # Look for action words or possessive patterns
                            if word_lower in action_words and i + 1 < len(user_words):
                                # Take the next 1-3 words as potential document name
                                potential_name_words = []
                                for j in range(i + 1, min(i + 4, len(user_words))):
                                    next_word = user_words[j].lower()
                                    # Stop if we hit another action word or common stop word
                                    if next_word in action_words or next_word in stop_words:
                                        break
                                    potential_name_words.append(user_words[j])
                                
                                if potential_name_words:
                                    document_name = " ".join(potential_name_words)
                                    # Capitalize properly
                                    document_name = " ".join([w.capitalize() for w in document_name.split()])
                                    logger.info(f"Extracted document name '{document_name}' from user message")
                                    break
                    
                    # Priority 4: Fallback to generic name
                    if not document_name or document_name == "New Document":
                        document_name = f"Document {len(documents_list) + 1}"
                        logger.warning(f"Using fallback document name: {document_name}")
                    
                    logger.info(f"Creating document with name: '{document_name}'")
                    
                    # Get initial content if provided in decision
                    initial_content = decision.get("document_content") or ""
                    
                    # Validate document name and content before creation
                    validation_result = DocumentValidator.validate_create(
                        document_name=document_name,
                        content=initial_content
                    )
                    
                    if not validation_result.is_valid:
                        logger.warning(f"Document creation validation failed: {validation_result.errors}")
                        decision['creation_error'] = {
                            'type': 'validation',
                            'message': f"Document creation validation failed: {', '.join(validation_result.errors)}"
                        }
                        # Don't proceed with creation if validation fails
                        created_document = None
                    else:
                        # Validation passed - proceed with creation
                        # Perform web search if needed for document creation (using WebSearchService)
                        if decision.get("needs_web_search") and decision.get("search_query"):
                            logger.info(f"Performing web search for document creation: {decision['search_query']}")
                            with tracer.start_as_current_span("agent.web_search_for_create") as web_span:
                                web_span.set_attribute("web_search.query", decision["search_query"])
                                
                                # Use WebSearchService for search with retry logic
                                web_search_result_obj_create = await self.web_search_service.search_with_retry(
                                    initial_query=decision["search_query"],
                                    user_message=user_message,
                                    context=f"Project: {project.name if project else 'Unknown'}, Creating document: {document_name}"
                                )
                                
                                web_search_results_for_create = web_search_result_obj_create.get_best_results()
                                if web_search_results_for_create:
                                    initial_content = f"{initial_content}\n\n{web_search_results_for_create}" if initial_content else web_search_results_for_create
                                
                                # Store web search result for later use in response
                                web_search_result_obj = web_search_result_obj_create
                                web_search_performed = len(web_search_result_obj_create.attempts) > 0
                                
                                web_span.set_attribute("web_search.attempts", len(web_search_result_obj_create.attempts))
                                web_span.set_attribute("web_search.was_retried", web_search_result_obj_create.was_retried())
                        
                        try:
                            if self.document_service:
                                # Note: create_document requires project_id as separate parameter
                                created_document_obj = self.document_service.create_document(
                                user_id=user_id,
                                project_id=project_id,
                                document_data=DocumentCreate(
                                    name=document_name,
                                    project_id=project_id,
                                    standing_instruction=decision.get("standing_instruction") or "",
                                    content=initial_content
                                )
                            )
                                created_document = {
                                    "id": created_document_obj.id,
                                    "name": created_document_obj.name,
                                    "standing_instruction": created_document_obj.standing_instruction,
                                    "content": created_document_obj.content,
                                    "project_id": created_document_obj.project_id,
                                    "user_id": created_document_obj.user_id,
                                    "created_at": created_document_obj.created_at,
                                    "updated_at": created_document_obj.updated_at
                                }
                                logger.info(f"Document {created_document_obj.id} created successfully")
                                span.set_attribute("agent.document_created", True)
                            else:
                                logger.warning("DocumentService not available, cannot create document")
                        except ValidationError as ve:
                            # Handle validation errors (e.g., duplicate document name)
                            error_message = str(ve)
                            logger.warning(f"Document creation validation error: {error_message}")
                            span.record_exception(ve)
                            # Store error info for better user feedback
                            created_document = None
                            # Check if it's a duplicate name error
                            if "already exists" in error_message.lower():
                                # Try to find the existing document with this name
                                existing_doc = None
                                for doc in documents_list:
                                    if doc.get('name', '').lower() == document_name.lower():
                                        existing_doc = doc
                                        break
                                # Store error context for response formatting
                                decision['creation_error'] = {
                                    'type': 'duplicate_name',
                                    'message': error_message,
                                    'document_name': document_name,
                                    'existing_document_id': existing_doc.get('id') if existing_doc else None
                                }
                            else:
                                decision['creation_error'] = {
                                    'type': 'validation',
                                    'message': error_message
                                }
                        except Exception as e:
                            logger.error(f"Error creating document: {e}")
                            span.record_exception(e)
                            created_document = None
                            decision['creation_error'] = {
                                'type': 'unknown',
                                'message': str(e)
                            }
                
                return {
                    "decision": decision,
                    "updated_document": updated_document,
                    "created_document": created_document,
                    "web_search_performed": web_search_performed,
                    "web_search_results": web_search_results if web_search_performed else None,
                    "web_search_result": web_search_result_obj  # Full WebSearchResult object with all attempts
                }
            except Exception as e:
                logger.error(f"Error processing agent action: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                self.document_repo.rollback()
                raise
    
    async def process_agent_action_with_chat(
        self,
        user_id: int,
        request: AgentActionRequest,
        chat_service: ChatService
    ) -> AgentActionResponse:
        """
        Process agent action with full chat orchestration.
        
        This method handles:
        - Chat creation/retrieval
        - User message storage
        - Agent action processing
        - Agent response formatting
        - Agent message storage
        - Response schema conversion
        
        Args:
            user_id: User ID
            request: Agent action request
            chat_service: Chat service instance
        
        Returns:
            AgentActionResponse with all processed data
        """
        logger.info(f"Processing agent action with chat for user {user_id}, chat_id: {request.chat_id}")
        
        with tracer.start_as_current_span("agent.process_agent_action_with_chat") as span:
            span.set_attribute("agent.user_id", user_id)
            span.set_attribute("agent.chat_id", request.chat_id)
            span.set_attribute("agent.project_id", request.project_id)
            span.set_attribute("agent.message_length", len(request.message))
            
            # Get or create chat
            chat = await self._get_or_create_chat(user_id, request, chat_service, span)
            
            # Store user message
            user_message = self._store_user_message(user_id, chat.id, request.message, chat_service)
            
            # Get chat history for context (excluding the message we just added)
            chat_history_for_llm = self._build_chat_history(chat_service, user_id, chat.id)
            
            # Process agent action
            result = await self.process_agent_action(
                user_id=user_id,
                user_message=request.message,
                project_id=request.project_id or chat.project_id,
                document_id=request.document_id,
                chat_history=chat_history_for_llm
            )
        
            # Prepare agent response message
            decision = result["decision"]
            should_edit = decision.get("should_edit", False)
            should_create = decision.get("should_create", False)
            needs_clarification = decision.get("needs_clarification", False)
            pending_confirmation = decision.get("pending_confirmation", False)
            conversational_response = decision.get("conversational_response")
            intent_statement = decision.get("intent_statement")
            change_summary = decision.get("change_summary")
            clarification_question = decision.get("clarification_question")
            confirmation_prompt = decision.get("confirmation_prompt")
            
            # Log response formatting details
            logger.info(f"Response formatting: should_edit={should_edit}, should_create={should_create}, "
                        f"updated_document={'present' if result.get('updated_document') else 'missing'}, "
                        f"created_document={'present' if result.get('created_document') else 'missing'}, "
                        f"web_search_performed={result.get('web_search_performed')}, "
                        f"web_search_result={'present' if result.get('web_search_result') else 'missing'}, "
                        f"content_summary={'present' if decision.get('content_summary') else 'missing'}, "
                        f"change_summary={'present' if change_summary else 'missing'}, "
                        f"intent_statement={'present' if intent_statement else 'missing'}")
            if result.get('web_search_result'):
                logger.info(f"Web search result details: attempts={len(result.get('web_search_result').attempts)}, "
                            f"was_retried={result.get('web_search_result').was_retried()}")
            
            # Format agent response content based on decision type
            if needs_clarification:
                # Need more information from user
                agent_response_content = clarification_question or "Could you please provide more details about what you'd like me to do?"
            
            elif pending_confirmation:
                # Need user confirmation before proceeding
                agent_response_content = confirmation_prompt or "This action requires confirmation. Should I proceed?"
            
            elif should_create:
                # Document creation requested - format response with action and content summary
                if result.get("created_document"):
                    # SUCCESS: Document was created
                    created_doc = result["created_document"]
                    parts = []
                    
                    # Part 1: Action summary (what was done) - use past tense
                    if intent_statement:
                        # Convert future tense to past tense for clarity
                        intent = intent_statement.replace("I'll create", "I've created").replace("I will create", "I've created")
                        parts.append(intent)
                    else:
                        parts.append(f"I've created the document '{created_doc['name']}' in this project.")
                    
                    # Part 2: Content summary (what's in the document)
                    # This helps user understand what content was added without reading the full document
                    content_summary = decision.get("content_summary")
                    if content_summary:
                        parts.append(f"\n\n**Document Content Summary:**\n{content_summary}")
                    elif decision.get("document_content"):
                        # Fallback: if no summary provided, show a preview of the content
                        doc_content = decision.get("document_content", "")
                        if doc_content:
                            preview = doc_content[:200] + "..." if len(doc_content) > 200 else doc_content
                            parts.append(f"\n\n**Initial Content Preview:**\n{preview}")
                    
                    # Part 3: Web search details (if applicable)
                    web_search_result = result.get("web_search_result")
                    if web_search_result and web_search_result.attempts:
                        parts.append("\n\n**Web Search Details:**")
                        for attempt in web_search_result.attempts:
                            parts.append(f"\n**Search Query {attempt.attempt_number}:** `{attempt.query}`")
                            if attempt.summary:
                                parts.append(f"**Results Summary:** {attempt.summary}")
                            if attempt.quality_score is not None:
                                parts.append(f"**Quality Score:** {attempt.quality_score:.2f}/1.0")
                            if attempt.retry_reason:
                                parts.append(f"**Retry Reason:** {attempt.retry_reason}")
                            if attempt.attempt_number < len(web_search_result.attempts):
                                parts.append("")  # Add spacing between attempts
                    
                    # Join all parts with newlines for better readability
                    agent_response_content = "\n".join(parts)
                else:
                    # FAILURE: Document creation failed - provide helpful error message
                    parts = []
                    creation_error = decision.get('creation_error', {})
                    error_type = creation_error.get('type', 'unknown')
                    
                    if error_type == 'duplicate_name':
                        # Document with this name already exists - suggest editing instead
                        existing_doc_id = creation_error.get('existing_document_id')
                        document_name = creation_error.get('document_name', decision.get('document_name', 'Unknown'))
                        
                        parts.append(f"A document named '{document_name}' already exists in this project.")
                        if existing_doc_id:
                            parts.append(f"I can add this content to the existing document instead. Would you like me to update '{document_name}' with the new content?")
                        else:
                            parts.append("Would you like me to:")
                        parts.append("1. Add this content to the existing document")
                        parts.append("2. Create a new document with a different name")
                        
                        if intent_statement:
                            parts.append(f"\n\nOriginal intent: {intent_statement}")
                    else:
                        # Other validation or unknown errors - be specific
                        error_type = creation_error.get('type', 'unknown')
                        error_msg = creation_error.get('message', 'Unknown error')
                        
                        if error_type == 'validation':
                            # Validation errors - show specific issues
                            parts.append(f"I tried to create the document but validation found issues:")
                            if 'validation failed' in error_msg.lower():
                                # Extract specific errors from message
                                parts.append(f"- {error_msg}")
                            else:
                                parts.append(f"- {error_msg}")
                            parts.append("\nPlease fix these issues and try again.")
                        elif not decision.get("document_name"):
                            # Missing document name
                            parts.append("I cannot create a document without a name.")
                            parts.append("Please specify a name, like 'Create a document called Recipes'.")
                        else:
                            # Unknown error - but still be specific
                            document_name = decision.get('document_name', 'Unknown')
                            parts.append(f"I attempted to create a document called '{document_name}', but it wasn't created successfully.")
                            if error_msg and error_msg != 'Unknown error':
                                parts.append(f"\n**Error:** {error_msg}")
                                parts.append("\nPlease check the document name or try again with a different name.")
                            else:
                                parts.append("\nPlease try again or check if a document with that name already exists.")
                        
                        if intent_statement:
                            parts.append(f"\n\n**Original intent:** {intent_statement}")
                    
                    agent_response_content = "\n".join(parts)
            
            elif should_edit and result.get("updated_document"):
                # Edit was successful - format response with action summary and content summary
                parts = []
                
                # Part 1: Action summary (what was done)
                if intent_statement:
                    parts.append(intent_statement)
                
                # Log response building details
                logger.info(f"Building edit response: intent_statement={'present' if intent_statement else 'missing'}, "
                            f"content_summary={'present' if decision.get('content_summary') else 'missing'}, "
                            f"change_summary={'present' if change_summary else 'missing'}, "
                            f"web_search_result={'present' if result.get('web_search_result') else 'missing'}, "
                            f"web_search_attempts={len(result.get('web_search_result').attempts) if result.get('web_search_result') else 0}")
                
                # Part 2: Content summary (what actually changed/added)
                # This is the detailed summary of the content that was added or changed
                # It helps the user understand what's now in the document
                content_summary = decision.get("content_summary")
                if content_summary:
                    parts.append(f"\n\n**Content Summary:**\n{content_summary}")
                elif change_summary:
                    # Fallback: if no content_summary provided, use change_summary
                    parts.append(f"\n\n**Changes:** {change_summary}")
                
                # Part 3: Validation warnings (if any)
                validation_warnings = decision.get("validation_warnings")
                if validation_warnings:
                    parts.append(f"\n\n**Note:** {', '.join(validation_warnings)}")
                
                # Part 4: Web search details (if applicable)
                web_search_result = result.get("web_search_result")
                if web_search_result and web_search_result.attempts:
                    parts.append("\n\n**Web Search Details:**")
                    for attempt in web_search_result.attempts:
                        parts.append(f"\n**Search Query {attempt.attempt_number}:** `{attempt.query}`")
                        if attempt.summary:
                            parts.append(f"**Results Summary:** {attempt.summary}")
                        if attempt.quality_score is not None:
                            parts.append(f"**Quality Score:** {attempt.quality_score:.2f}/1.0")
                        if attempt.retry_reason:
                            parts.append(f"**Retry Reason:** {attempt.retry_reason}")
                        if attempt.attempt_number < len(web_search_result.attempts):
                            parts.append("")  # Add spacing between attempts
                
                # Join all parts with newlines for better readability in chat
                if parts:
                    agent_response_content = "\n".join(parts)
                else:
                    agent_response_content = "I've updated the document content."
            
            elif should_edit:
                # Edit was attempted but failed - provide specific diagnostic
                parts = []
                
                # Check for validation errors
                validation_errors = decision.get("validation_errors")
                if validation_errors:
                    parts.append("I rewrote the document but validation found issues:")
                    for error in validation_errors:
                        parts.append(f"- {error}")
                    parts.append("\nI can retry with fixes. Should I proceed?")
                else:
                    # Generic failure - but still be specific
                    parts.append("I understood your request, but couldn't update the document.")
                    if decision.get("reasoning"):
                        parts.append(f"Reason: {decision['reasoning']}")
                    else:
                        parts.append("The document may not exist or there was an error. Please check the document ID or try again.")
                
                agent_response_content = "\n".join(parts)
            
            else:
                # No edit - use conversational response if available, otherwise generate one
                # CRITICAL: If web search was performed, always generate response to include results and post-processing
                web_search_performed = result.get("web_search_performed", False)
                if conversational_response and not web_search_performed:
                    agent_response_content = conversational_response
                else:
                    # Generate a conversational response for questions/general conversation
                    # This ensures web search results are included and post-processing runs
                    logger.debug("Generating conversational response" + (" (web search performed, overriding decision's conversational_response)" if conversational_response and web_search_performed else ""))
                    
                    # Get project documents for context if user is asking about content
                    project_id_to_check = request.project_id or chat.project_id
                    project_documents_content = None
                    if project_id_to_check:
                        project_documents = self.document_repo.get_by_project_id(project_id_to_check)
                        if project_documents:
                            # Include document names and brief content summaries
                            project_documents_content = "\n\n".join([
                                f"Document: {d.name}\nContent: {d.content[:500]}..." if len(d.content) > 500 else f"Document: {d.name}\nContent: {d.content}"
                                for d in project_documents
                            ])
                    
                    # Build context with document content if available and user is asking for info
                    context = result.get("decision", {}).get("reasoning", "")
                    user_message_lower = request.message.lower()
                    
                    # Check if user is asking about location/status of documents
                    is_location_question = any(keyword in user_message_lower for keyword in ["where", "where did", "where is", "where are", "what did you", "what did i"])
                    
                    if project_documents_content and any(keyword in user_message_lower for keyword in ["summarize", "read", "tell me about", "what's in", "show me", "describe", "where", "where did", "where is"]):
                        context = f"Project documents:\n{project_documents_content}\n\n{context if context else 'User is asking about the project documents.'}"
                    
                    # For location questions, extract recent document operations from chat history
                    if is_location_question and chat_history_for_llm:
                        recent_operations = []
                        # Look at recent messages (last 5) for document operations
                        for msg in reversed(chat_history_for_llm[-5:]):
                            role = msg.get("role", "")
                            if hasattr(role, 'value'):
                                role = role.value
                            elif not isinstance(role, str):
                                role = str(role).lower()
                            
                            if role in ["assistant", "system"]:
                                content = msg.get("content", "")
                                metadata = msg.get("metadata", {})
                                decision = metadata.get("decision", {})
                                
                                # Check if this message was about creating/editing a document
                                if decision.get("should_create") or decision.get("should_edit"):
                                    doc_name = decision.get("document_name") or "a document"
                                    doc_id = decision.get("document_id")
                                    action = "created" if decision.get("should_create") else "updated"
                                    intent = decision.get("intent_statement", f"I {action} {doc_name}")
                                    
                                    # Try to get actual document name from database if we have doc_id
                                    if doc_id:
                                        try:
                                            doc = self.document_repo.get_by_id(doc_id)
                                            if doc:
                                                doc_name = doc.name
                                        except Exception:
                                            pass
                                    
                                    recent_operations.append(f"- {intent} (Document: {doc_name})")
                        
                        if recent_operations:
                            context = f"Recent document operations from conversation history:\n" + "\n".join(recent_operations[:3]) + "\n\n" + context
                    
                    # Include web search results if available for conversational responses
                    web_search_results_for_conversation = result.get("web_search_results")
                    
                    # Add detailed logging to verify web search results are being passed
                    logger.info(f"[AGENT] Preparing conversational response: "
                               f"has_results={web_search_results_for_conversation is not None}, "
                               f"results_length={len(web_search_results_for_conversation) if web_search_results_for_conversation else 0}, "
                               f"result_keys={list(result.keys())}, "
                               f"web_search_performed={web_search_performed}, "
                               f"conversational_response_from_decision={'present' if conversational_response else 'missing'}")
                    
                    if web_search_results_for_conversation:
                        logger.info(f"[AGENT] Web search results preview (first 500 chars): {web_search_results_for_conversation[:500]}")
                    
                    agent_response_content = await self.llm_service.generate_conversational_response(
                        request.message,
                        context,
                        chat_history=chat_history_for_llm,
                        web_search_results=web_search_results_for_conversation
                    )
                    
                    logger.info(f"[AGENT] Conversational response received, length: {len(agent_response_content)}, preview: {agent_response_content[:200]}")
            
            # Store agent response
            logger.debug(f"Storing agent response in chat {chat.id}")
            with tracer.start_as_current_span("agent.store_agent_message") as msg_span:
                msg_span.set_attribute("message.operation", "store_agent_message")
                msg_span.set_attribute("message.chat_id", chat.id)
                agent_message = chat_service.add_message(
                    user_id,
                    chat.id,
                    ChatMessageCreate(
                        role=MessageRole.ASSISTANT,
                        content=agent_response_content,
                        metadata={
                            "decision": result["decision"],
                            "web_search_performed": result.get("web_search_performed", False),
                            "document_updated": result.get("updated_document") is not None,
                            "needs_clarification": needs_clarification,
                            "pending_confirmation": pending_confirmation,
                            "should_create": should_create
                        }
                    )
                )
                msg_span.set_attribute("message.id", agent_message.id)
            
            span.set_attribute("agent.success", result.get("updated_document") is not None or result.get("created_document") is not None)
            
            # Build and return response
            return self._build_response(result, agent_message, request, chat, user_id)
