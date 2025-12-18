from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import User, Chat, ChatMessage, MessageRole
from ...schemas import AgentActionRequest, AgentActionResponse, Module as ModuleSchema, ChatMessage as ChatMessageSchema
from ...auth import get_current_user
from ...agent import process_agent_action
from ...openai_client import generate_conversational_response

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/act", response_model=AgentActionResponse)
async def agent_action(
    request: AgentActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process agent action: detect intent, edit modules, perform web search"""
    # Get or create chat
    chat = None
    if request.chat_id:
        chat = db.query(Chat).filter(
            Chat.id == request.chat_id,
            Chat.user_id == current_user.id
        ).first()
        if chat:
            # Validate that the chat belongs to the requested module (if module_id is provided)
            if request.module_id and chat.module_id != request.module_id:
                # Chat exists but belongs to a different module - create a new chat for this module
                chat = None
        # If chat not found or doesn't match module, we'll create a new one below
    
    if not chat:
        # Create new chat - use module_id from request or try to get from existing chat
        module_id_to_use = request.module_id
        if not module_id_to_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="module_id is required to create a new chat"
            )
        chat = Chat(
            user_id=current_user.id,
            module_id=module_id_to_use
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
    
    # Store user message
    user_message = ChatMessage(
        chat_id=chat.id,
        role=MessageRole.USER,
        content=request.message,
        message_metadata={}
    )
    db.add(user_message)
    db.commit()
    
    # Process agent action
    result = await process_agent_action(
        db=db,
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
    agent_message = ChatMessage(
        chat_id=chat.id,
        role=MessageRole.ASSISTANT,
        content=agent_response_content,
        message_metadata={
            "decision": result["decision"],
            "web_search_performed": result.get("web_search_performed", False),
            "module_updated": result.get("updated_module") is not None
        }
    )
    db.add(agent_message)
    db.commit()
    db.refresh(agent_message)
    
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

