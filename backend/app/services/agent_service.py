from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..repositories import ModuleRepository, ChatRepository
from ..models import Module, ChatMessage, MessageRole
from ..schemas import AgentActionRequest, AgentActionResponse, ChatCreate, ChatMessageCreate, Module as ModuleSchema, ChatMessage as ChatMessageSchema
from ..exceptions import ValidationError
from ..core.events import event_bus, AgentActionCompletedEvent
from ..core.telemetry import get_tracer
from opentelemetry import trace
from .llm_service import LLMService
from .chat_service import ChatService
from ..clients import search_web
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class AgentService:
    """Service for agent operations"""
    
    def __init__(self, db: Session, llm_service: LLMService):
        """
        Initialize agent service
        
        Args:
            db: Database session
            llm_service: LLM service (required, injected via dependency injection)
        """
        self.module_repo = ModuleRepository(db)
        self.chat_repo = ChatRepository(db)
        self.db = db
        self.llm_service = llm_service
    
    async def process_agent_action(
        self,
        user_id: int,
        user_message: str,
        module_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process agent action: detect intent, decide on edits, perform web search if needed,
        and rewrite module content.
        """
        logger.info(f"Processing agent action for user {user_id}, module_id: {module_id}")
        
        with tracer.start_as_current_span("agent.process_agent_action") as span:
            span.set_attribute("agent.user_id", user_id)
            span.set_attribute("agent.module_id", module_id)
            span.set_attribute("agent.message_length", len(user_message))
            
            try:
                # Get all user modules
                with tracer.start_as_current_span("agent.get_user_modules") as db_span:
                    db_span.set_attribute("db.operation", "get_user_modules")
                    user_modules = self.module_repo.get_by_user_id(user_id)
                    db_span.set_attribute("db.result_count", len(user_modules))
                modules_list = [
                    {
                        "id": m.id,
                        "name": m.name,
                        "standing_instruction": m.standing_instruction,
                        "content": m.content
                    }
                    for m in user_modules
                ]
                
                # Get current module if specified
                current_module = None
                if module_id:
                    with tracer.start_as_current_span("agent.get_current_module") as db_span:
                        db_span.set_attribute("db.operation", "get_current_module")
                        module = self.module_repo.get_by_user_and_id(user_id, module_id)
                        if module:
                            current_module = {
                                "id": module.id,
                                "name": module.name,
                                "standing_instruction": module.standing_instruction,
                                "content": module.content
                            }
                            db_span.set_attribute("db.module_found", True)
                        else:
                            db_span.set_attribute("db.module_found", False)
                
                # Get agent decision
                decision = await self.llm_service.get_agent_decision(user_message, modules_list, current_module)
                span.set_attribute("agent.decision.should_edit", decision.get("should_edit", False))
                span.set_attribute("agent.decision.module_id", decision.get("module_id"))
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
                
                # Rewrite module if decision says so
                updated_module = None
                if decision.get("should_edit") and decision.get("module_id"):
                    target_module_id = decision["module_id"]
                    with tracer.start_as_current_span("agent.get_target_module") as db_span:
                        db_span.set_attribute("db.operation", "get_target_module")
                        target_module = self.module_repo.get_by_user_and_id(user_id, target_module_id)
                    
                    if target_module:
                        logger.info(f"Rewriting module {target_module_id}")
                        # Rewrite the entire module content
                        new_content = await self.llm_service.rewrite_module_content(
                            user_message=user_message,
                            standing_instruction=target_module.standing_instruction,
                            current_content=target_module.content,
                            web_search_results=web_search_results
                        )
                        
                        # Update module using repository
                        with tracer.start_as_current_span("agent.update_module") as db_span:
                            db_span.set_attribute("db.operation", "update_module")
                            db_span.set_attribute("db.module_id", target_module_id)
                            updated_module_obj = self.module_repo.update(
                                target_module_id,
                                content=new_content
                            )
                            
                            if updated_module_obj:
                                # Commit the transaction
                                self.module_repo.commit()
                                self.db.refresh(updated_module_obj)
                                
                                updated_module = {
                                    "id": updated_module_obj.id,
                                    "name": updated_module_obj.name,
                                    "standing_instruction": updated_module_obj.standing_instruction,
                                    "content": updated_module_obj.content,
                                    "user_id": updated_module_obj.user_id,
                                    "created_at": updated_module_obj.created_at,
                                    "updated_at": updated_module_obj.updated_at
                                }
                                logger.info(f"Module {target_module_id} updated successfully")
                                db_span.set_attribute("db.update_success", True)
                                span.set_attribute("agent.module_updated", True)
                            else:
                                db_span.set_attribute("db.update_success", False)
                                span.set_attribute("agent.module_updated", False)
                
                return {
                    "decision": decision,
                    "updated_module": updated_module,
                    "web_search_performed": web_search_performed,
                    "web_search_results": web_search_results if web_search_performed else None
                }
            except Exception as e:
                logger.error(f"Error processing agent action: {e}")
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                self.module_repo.rollback()
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
            span.set_attribute("agent.module_id", request.module_id)
            span.set_attribute("agent.message_length", len(request.message))
            
            # Get or create chat
            chat = None
            if request.chat_id:
                with tracer.start_as_current_span("agent.get_chat") as chat_span:
                    chat_span.set_attribute("chat.operation", "get_chat")
                    try:
                        chat = chat_service.get_chat(user_id, request.chat_id)
                        chat_span.set_attribute("chat.found", True)
                        # Validate that the chat belongs to the requested module (if module_id is provided)
                        if request.module_id and chat.module_id != request.module_id:
                            # Chat exists but belongs to a different module - create a new chat for this module
                            logger.info(f"Chat {request.chat_id} belongs to different module, creating new chat")
                            chat = None
                            chat_span.set_attribute("chat.module_mismatch", True)
                    except Exception as e:
                        logger.warning(f"Failed to get chat {request.chat_id}: {e}")
                        chat_span.set_attribute("chat.found", False)
                        chat_span.record_exception(e)
                        chat = None
            
            if not chat:
                # Create new chat - use module_id from request
                module_id_to_use = request.module_id
                if not module_id_to_use:
                    raise ValidationError("module_id is required to create a new chat")
                
                logger.info(f"Creating new chat for user {user_id}, module_id: {module_id_to_use}")
                with tracer.start_as_current_span("agent.create_chat") as chat_span:
                    chat_span.set_attribute("chat.operation", "create_chat")
                    chat_span.set_attribute("chat.module_id", module_id_to_use)
                    chat = chat_service.create_chat(
                        user_id,
                        ChatCreate(module_id=module_id_to_use)
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
            
            # Process agent action
            result = await self.process_agent_action(
                user_id=user_id,
                user_message=request.message,
                module_id=request.module_id or chat.module_id
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
                # Module creation requested (not implemented yet, but prepared)
                agent_response_content = intent_statement or "I'll create a new module for you."
                # TODO: Implement module creation flow
            
            elif should_edit and result.get("updated_module"):
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
                    agent_response_content = "I've updated the module content."
            
            elif should_edit:
                # Edit was attempted but failed
                agent_response_content = "I understood your request, but couldn't update the module."
                if decision.get("reasoning"):
                    agent_response_content += f" {decision['reasoning']}"
            
            else:
                # No edit - use conversational response if available, otherwise generate one
                if conversational_response:
                    agent_response_content = conversational_response
                else:
                    # Generate a conversational response for questions/general conversation
                    logger.debug("Generating conversational response")
                    
                    # If we have a current module and user is asking to summarize/read, pass module content
                    current_module_content = None
                    module_id_to_check = request.module_id or chat.module_id
                    if module_id_to_check:
                        module = self.module_repo.get_by_user_and_id(user_id, module_id_to_check)
                        if module:
                            current_module_content = module.content
                    
                    # Build context with module content if available and user is asking for info
                    context = result.get("decision", {}).get("reasoning", "")
                    user_message_lower = request.message.lower()
                    if current_module_content and any(keyword in user_message_lower for keyword in ["summarize", "read", "tell me about", "what's in", "show me", "describe"]):
                        context = f"Module content:\n{current_module_content}\n\n{context if context else 'User is asking about the module content.'}"
                    
                    agent_response_content = await self.llm_service.generate_conversational_response(
                        request.message,
                        context
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
                            "module_updated": result.get("updated_module") is not None,
                            "needs_clarification": needs_clarification,
                            "pending_confirmation": pending_confirmation,
                            "should_create": should_create
                        }
                    )
                )
                msg_span.set_attribute("message.id", agent_message.id)
            
            # Convert updated module to schema if exists
            updated_module_schema = None
            if result.get("updated_module"):
                updated_module_schema = ModuleSchema(**result["updated_module"])
            
            # Publish event for cross-cutting concerns (analytics, monitoring)
            event_bus.publish(AgentActionCompletedEvent(
                user_id=user_id,
                chat_id=chat.id,
                module_id=request.module_id or chat.module_id,
                action_type="agent_action",
                success=result.get("updated_module") is not None,
                metadata={
                    "should_edit": should_edit,
                    "should_create": should_create,
                    "needs_clarification": needs_clarification,
                    "pending_confirmation": pending_confirmation,
                    "web_search_performed": result.get("web_search_performed", False),
                    "module_updated": result.get("updated_module") is not None
                }
            ))
            
            span.set_attribute("agent.success", result.get("updated_module") is not None)
            
            # Build and return response
            return AgentActionResponse(
                module=updated_module_schema,
                chat_message=ChatMessageSchema.model_validate(agent_message),
                agent_decision=result["decision"],
                web_search_performed=result.get("web_search_performed", False)
            )
