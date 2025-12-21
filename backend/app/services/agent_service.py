from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..repositories import DocumentRepository, ProjectRepository, ChatRepository
from ..models import Document, Project, ChatMessage, MessageRole
from ..schemas import AgentActionRequest, AgentActionResponse, ChatCreate, ChatMessageCreate, Document as DocumentSchema, DocumentCreate, ChatMessage as ChatMessageSchema
from ..exceptions import ValidationError
from ..core.events import event_bus, AgentActionCompletedEvent
from ..core.telemetry import get_tracer
from opentelemetry import trace
from .llm_service import LLMService
from .chat_service import ChatService
from .document_service import DocumentService
from ..clients import search_web
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
        self.document_service = document_service
    
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
                span.set_attribute("agent.decision.should_edit", decision.get("should_edit", False))
                span.set_attribute("agent.decision.document_id", decision.get("document_id"))
                span.set_attribute("agent.decision.needs_web_search", decision.get("needs_web_search", False))
                
                web_search_performed = False
                web_search_results = None
                
                # Perform web search if needed
                if decision.get("needs_web_search") and decision.get("search_query"):
                    logger.info(f"Performing web search: {decision['search_query']}")
                    with tracer.start_as_current_span("agent.web_search") as web_span:
                        web_span.set_attribute("web_search.query", decision["search_query"])
                        web_search_results = search_web(decision["search_query"])
                        web_search_performed = True
                        web_span.set_attribute("web_search.results_count", len(web_search_results) if web_search_results else 0)
                
                # Rewrite document if decision says so
                updated_document = None
                if decision.get("should_edit") and decision.get("document_id"):
                    target_document_id = decision["document_id"]
                    with tracer.start_as_current_span("agent.get_target_document") as db_span:
                        db_span.set_attribute("db.operation", "get_target_document")
                        target_document = self.document_repo.get_by_user_and_id(user_id, target_document_id)
                    
                    if target_document:
                        logger.info(f"Rewriting document {target_document_id}")
                        # Rewrite the entire document content
                        new_content = await self.llm_service.rewrite_document_content(
                            user_message=user_message,
                            standing_instruction=target_document.standing_instruction,
                            current_content=target_document.content,
                            web_search_results=web_search_results
                        )
                        
                        # Update document using repository
                        with tracer.start_as_current_span("agent.update_document") as db_span:
                            db_span.set_attribute("db.operation", "update_document")
                            db_span.set_attribute("db.document_id", target_document_id)
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
                            else:
                                db_span.set_attribute("db.update_success", False)
                                span.set_attribute("agent.document_updated", False)
                
                # Handle document creation if requested
                created_document = None
                if decision.get("should_create") and project_id:
                    document_name = decision.get("document_name") or decision.get("intent_statement", "New Document")
                    # Extract document name from intent_statement if not provided
                    if not decision.get("document_name"):
                        # Try to extract name from intent_statement or user message
                        intent = decision.get("intent_statement", "")
                        if "document" in intent.lower() or "called" in intent.lower():
                            # Try to extract name from phrases like "create a document called X" or "new document for X"
                            parts = intent.split()
                            for i, part in enumerate(parts):
                                if part.lower() in ["called", "named", "for"] and i + 1 < len(parts):
                                    document_name = " ".join(parts[i+1:]).strip('"\'.,')
                                    break
                        if document_name == "New Document":
                            # Fallback: use a default name based on project or user message
                            document_name = f"Document {len(documents_list) + 1}"
                    
                    # Get initial content if provided in decision
                    initial_content = decision.get("document_content") or ""
                    
                    # Perform web search if needed for document creation
                    if decision.get("needs_web_search") and decision.get("search_query"):
                        logger.info(f"Performing web search for document creation: {decision['search_query']}")
                        with tracer.start_as_current_span("agent.web_search_for_create") as web_span:
                            web_span.set_attribute("web_search.query", decision["search_query"])
                            web_search_results_for_create = search_web(decision["search_query"])
                            if web_search_results_for_create:
                                initial_content = f"{initial_content}\n\n{web_search_results_for_create}" if initial_content else web_search_results_for_create
                    
                    try:
                        if self.document_service:
                            created_document_obj = self.document_service.create_document(
                                user_id=user_id,
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
                    except Exception as e:
                        logger.error(f"Error creating document: {e}")
                        span.record_exception(e)
                        created_document = None
                
                return {
                    "decision": decision,
                    "updated_document": updated_document,
                    "created_document": created_document,
                    "web_search_performed": web_search_performed,
                    "web_search_results": web_search_results if web_search_performed else None
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
            
            # Store user message
            logger.debug(f"Storing user message in chat {chat.id}")
            with tracer.start_as_current_span("agent.store_user_message") as msg_span:
                msg_span.set_attribute("message.operation", "store_user_message")
                msg_span.set_attribute("message.chat_id", chat.id)
                user_message = chat_service.add_message(
                    user_id,
                    chat.id,
                    ChatMessageCreate(
                        role=MessageRole.USER,
                        content=request.message,
                        metadata={}
                    )
                )
                msg_span.set_attribute("message.id", user_message.id)
            
            # Get chat history for context (excluding the message we just added)
            chat_messages_db = chat_service.get_chat_messages(user_id, chat.id)
            # Filter out the user message we just added to avoid duplication
            chat_history_for_llm = [
                {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, "content": msg.content}
                for msg in chat_messages_db[:-1]  # Exclude the last message (the one we just added)
            ]
            
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
            
            # Format agent response content based on decision type
            if needs_clarification:
                # Need more information from user
                agent_response_content = clarification_question or "Could you please provide more details about what you'd like me to do?"
            
            elif pending_confirmation:
                # Need user confirmation before proceeding
                agent_response_content = confirmation_prompt or "This action requires confirmation. Should I proceed?"
            
            elif should_create:
                # Document creation requested
                if result.get("created_document"):
                    created_doc = result["created_document"]
                    parts = []
                    if intent_statement:
                        parts.append(intent_statement)
                    parts.append(f"I've created the document '{created_doc['name']}' in this project.")
                    if result.get("web_search_performed"):
                        parts.append("I performed a web search to gather initial content.")
                    agent_response_content = " ".join(parts)
                else:
                    agent_response_content = intent_statement or "I'll create a new document for you, but encountered an issue. Please try again."
            
            elif should_edit and result.get("updated_document"):
                # Edit was successful - show what was done
                parts = []
                if intent_statement:
                    parts.append(intent_statement)
                if change_summary:
                    parts.append(f"**Changes made:** {change_summary}")
                if result.get("web_search_performed"):
                    parts.append("I performed a web search to ensure accuracy.")
                
                if parts:
                    agent_response_content = " ".join(parts)
                else:
                    agent_response_content = "I've updated the document content."
            
            elif should_edit:
                # Edit was attempted but failed
                agent_response_content = "I understood your request, but couldn't update the document."
                if decision.get("reasoning"):
                    agent_response_content += f" {decision['reasoning']}"
            
            else:
                # No edit - use conversational response if available, otherwise generate one
                if conversational_response:
                    agent_response_content = conversational_response
                else:
                    # Generate a conversational response for questions/general conversation
                    logger.debug("Generating conversational response")
                    
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
                    if project_documents_content and any(keyword in user_message_lower for keyword in ["summarize", "read", "tell me about", "what's in", "show me", "describe"]):
                        context = f"Project documents:\n{project_documents_content}\n\n{context if context else 'User is asking about the project documents.'}"
                    
                    agent_response_content = await self.llm_service.generate_conversational_response(
                        request.message,
                        context,
                        chat_history=chat_history_for_llm
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
            
            # Convert updated or created document to schema if exists
            updated_document_schema = None
            if result.get("updated_document"):
                updated_document_schema = DocumentSchema(**result["updated_document"])
            elif result.get("created_document"):
                updated_document_schema = DocumentSchema(**result["created_document"])
            
            # Publish event for cross-cutting concerns (analytics, monitoring)
            event_bus.publish(AgentActionCompletedEvent(
                user_id=user_id,
                chat_id=chat.id,
                project_id=request.project_id or chat.project_id,
                document_id=request.document_id or (result.get("updated_document", {}).get("id") if result.get("updated_document") else None) or (result.get("created_document", {}).get("id") if result.get("created_document") else None),
                action_type="agent_action",
                success=result.get("updated_document") is not None or result.get("created_document") is not None,
                metadata={
                    "should_edit": should_edit,
                    "should_create": should_create,
                    "needs_clarification": needs_clarification,
                    "pending_confirmation": pending_confirmation,
                    "web_search_performed": result.get("web_search_performed", False),
                    "document_updated": result.get("updated_document") is not None,
                    "document_created": result.get("created_document") is not None
                }
            ))
            
            span.set_attribute("agent.success", result.get("updated_document") is not None or result.get("created_document") is not None)
            
            # Build and return response
            return AgentActionResponse(
                document=updated_document_schema,
                chat_message=ChatMessageSchema.model_validate(agent_message),
                agent_decision=result["decision"],
                web_search_performed=result.get("web_search_performed", False)
            )
