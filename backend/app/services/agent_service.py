from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..repositories import ModuleRepository, ChatRepository
from ..models import Module, ChatMessage, MessageRole
from ..schemas import AgentActionRequest, AgentActionResponse, ChatCreate, ChatMessageCreate, Module as ModuleSchema, ChatMessage as ChatMessageSchema
from ..exceptions import ValidationError
from ..core.events import event_bus, AgentActionCompletedEvent
from .llm_service import LLMService
from .chat_service import ChatService
from ..clients import search_web
import logging

logger = logging.getLogger(__name__)


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
        
        try:
            # Get all user modules
            user_modules = self.module_repo.get_by_user_id(user_id)
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
                module = self.module_repo.get_by_user_and_id(user_id, module_id)
                if module:
                    current_module = {
                        "id": module.id,
                        "name": module.name,
                        "standing_instruction": module.standing_instruction,
                        "content": module.content
                    }
            
            # Get agent decision
            decision = await self.llm_service.get_agent_decision(user_message, modules_list, current_module)
            
            web_search_performed = False
            web_search_results = None
            
            # Perform web search if needed
            if decision.get("needs_web_search") and decision.get("search_query"):
                logger.info(f"Performing web search: {decision['search_query']}")
                web_search_results = search_web(decision["search_query"])
                web_search_performed = True
            
            # Rewrite module if decision says so
            updated_module = None
            if decision.get("should_edit") and decision.get("module_id"):
                target_module_id = decision["module_id"]
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
            
            return {
                "decision": decision,
                "updated_module": updated_module,
                "web_search_performed": web_search_performed,
                "web_search_results": web_search_results if web_search_performed else None
            }
        except Exception as e:
            logger.error(f"Error processing agent action: {e}")
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
        
        # Get or create chat
        chat = None
        if request.chat_id:
            try:
                chat = chat_service.get_chat(user_id, request.chat_id)
                # Validate that the chat belongs to the requested module (if module_id is provided)
                if request.module_id and chat.module_id != request.module_id:
                    # Chat exists but belongs to a different module - create a new chat for this module
                    logger.info(f"Chat {request.chat_id} belongs to different module, creating new chat")
                    chat = None
            except Exception as e:
                logger.warning(f"Failed to get chat {request.chat_id}: {e}")
                chat = None
        
        if not chat:
            # Create new chat - use module_id from request
            module_id_to_use = request.module_id
            if not module_id_to_use:
                raise ValidationError("module_id is required to create a new chat")
            
            logger.info(f"Creating new chat for user {user_id}, module_id: {module_id_to_use}")
            chat = chat_service.create_chat(
                user_id,
                ChatCreate(module_id=module_id_to_use)
            )
        
        # Store user message
        logger.debug(f"Storing user message in chat {chat.id}")
        user_message = chat_service.add_message(
            user_id,
            chat.id,
            ChatMessageCreate(
                role=MessageRole.USER,
                content=request.message,
                metadata={}
            )
        )
        
        # Process agent action
        result = await self.process_agent_action(
            user_id=user_id,
            user_message=request.message,
            module_id=request.module_id or chat.module_id
        )
        
        # Prepare agent response message
        decision = result["decision"]
        should_edit = decision.get("should_edit", False)
        conversational_response = decision.get("conversational_response")
        
        # Format agent response content
        if should_edit and result.get("updated_module"):
            # Edit was successful
            agent_response_content = "I've updated the module content."
            if decision.get("reasoning"):
                agent_response_content += f" {decision['reasoning']}"
            if result.get("web_search_performed"):
                agent_response_content += " I performed a web search to ensure accuracy."
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
                agent_response_content = await self.llm_service.generate_conversational_response(
                    request.message,
                    result.get("decision", {}).get("reasoning", "")
                )
        
        # Store agent response
        logger.debug(f"Storing agent response in chat {chat.id}")
        agent_message = chat_service.add_message(
            user_id,
            chat.id,
            ChatMessageCreate(
                role=MessageRole.ASSISTANT,
                content=agent_response_content,
                metadata={
                    "decision": result["decision"],
                    "web_search_performed": result.get("web_search_performed", False),
                    "module_updated": result.get("updated_module") is not None
                }
            )
        )
        
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
                "should_edit": decision.get("should_edit", False),
                "web_search_performed": result.get("web_search_performed", False),
                "module_updated": result.get("updated_module") is not None
            }
        ))
        
        # Build and return response
        return AgentActionResponse(
            module=updated_module_schema,
            chat_message=ChatMessageSchema.model_validate(agent_message),
            agent_decision=result["decision"],
            web_search_performed=result.get("web_search_performed", False)
        )
