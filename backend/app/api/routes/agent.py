from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...core.security import get_current_user
from ...models import User, Chat, ChatMessage, MessageRole
from ...schemas import AgentActionRequest, AgentActionResponse, Module as ModuleSchema, ChatMessage as ChatMessageSchema, ChatCreate, ChatMessageCreate
from ...services import AgentService, ChatService
from ...clients import generate_conversational_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/act", response_model=AgentActionResponse)
async def agent_action(
    request: AgentActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process agent action: detect intent, edit modules, perform web search"""
    agent_service = AgentService(db)
    chat_service = ChatService(db)
    
    # Get or create chat
    chat = None
    if request.chat_id:
        try:
            chat = chat_service.get_chat(current_user.id, request.chat_id)
            # Validate that the chat belongs to the requested module (if module_id is provided)
            if request.module_id and chat.module_id != request.module_id:
                # Chat exists but belongs to a different module - create a new chat for this module
                chat = None
        except Exception:
            chat = None
    
    if not chat:
        # Create new chat - use module_id from request
        module_id_to_use = request.module_id
        if not module_id_to_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_id is required to create a new chat"
            )
        chat = chat_service.create_chat(
            current_user.id,
            ChatCreate(module_id=module_id_to_use)
        )
    
    # Store user message
    user_message = chat_service.add_message(
        current_user.id,
        chat.id,
        ChatMessageCreate(
            role=MessageRole.USER,
            content=request.message,
            metadata={}
        )
    )
    
    # Process agent action
    result = await agent_service.process_agent_action(
        user_id=current_user.id,
        user_message=request.message,
        module_id=request.module_id or chat.module_id
    )
    
    # Prepare agent response message
    decision = result["decision"]
    should_edit = decision.get("should_edit", False)
    
    # Check if there's a conversational response from the agent
    conversational_response = decision.get("conversational_response")
    
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
            agent_response_content = await generate_conversational_response(
                request.message,
                result.get("decision", {}).get("reasoning", "")
            )
    
    # Store agent response
    agent_message = chat_service.add_message(
        current_user.id,
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
    
    return AgentActionResponse(
        module=updated_module_schema,
        chat_message=ChatMessageSchema.model_validate(agent_message),
        agent_decision=result["decision"],
        web_search_performed=result.get("web_search_performed", False)
    )
