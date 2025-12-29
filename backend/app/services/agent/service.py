"""
Agent Service

Main service for agent operations including chat orchestration,
document operations, and response generation.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ...repositories import DocumentRepository, ProjectRepository, ChatRepository
from ...models import Project, ChatMessage, MessageRole
from ...schemas import AgentActionRequest, AgentActionResponse, ChatCreate, ChatMessageCreate, Document as DocumentSchema, ChatMessage as ChatMessageSchema
from ...exceptions import ValidationError
from ...core.events import event_bus, AgentActionCompletedEvent
from ...core.telemetry import get_tracer
from opentelemetry import trace
from ..llm_service import LLMService
from ..chat_service import ChatService
from ..document_service import DocumentService
from ..web_search import WebSearchService
from .name_extractor import DocumentNameExtractor
from .document_updater import DocumentUpdater
from .document_creator import DocumentCreator
from .response_formatter import AgentResponseFormatter
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
        self.response_formatter = AgentResponseFormatter(llm_service, self.document_repo)
    
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
                    
                    # Use DocumentUpdater to handle update logic
                    document_updater = DocumentUpdater(
                        self.document_repo,
                        self.llm_service,
                        self.db,
                        web_search_results=web_search_results
                    )
                    updated_document = await document_updater.update_document(
                        decision=decision,
                        user_id=user_id,
                        user_message=user_message,
                        target_document_id=target_document_id,
                        span=span
                    )
                
                # Handle document creation if requested
                created_document = None
                if decision.get("should_create") and project_id:
                    # Use DocumentCreator to handle creation logic
                    document_creator = DocumentCreator(
                        self.document_service,
                        self.document_repo,
                        self.llm_service,
                        self.web_search_service
                    )
                    created_document, web_search_result_obj_create = await document_creator.create_document(
                        decision=decision,
                        user_id=user_id,
                        project_id=project_id,
                        user_message=user_message,
                        documents_list=documents_list,
                        project=project,
                        span=span
                    )
                    # If document creation performed web search, use that result
                    if web_search_result_obj_create:
                        web_search_result_obj = web_search_result_obj_create
                        web_search_performed = len(web_search_result_obj_create.attempts) > 0
                        web_search_results = web_search_result_obj_create.get_best_results()
                
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
        
            # Format agent response using AgentResponseFormatter
            decision = result["decision"]
            agent_response_content = await self.response_formatter.format_response(
                result=result,
                request=request,
                chat=chat,
                chat_history_for_llm=chat_history_for_llm
            )
            
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
                            "decision": decision,
                            "web_search_performed": result.get("web_search_performed", False),
                            "document_updated": result.get("updated_document") is not None,
                            "needs_clarification": decision.get("needs_clarification", False),
                            "pending_confirmation": decision.get("pending_confirmation", False),
                            "should_create": decision.get("should_create", False)
                        }
                    )
                )
                msg_span.set_attribute("message.id", agent_message.id)
            
            span.set_attribute("agent.success", result.get("updated_document") is not None or result.get("created_document") is not None)
            
            # Build and return response
            return self._build_response(result, agent_message, request, chat, user_id)

