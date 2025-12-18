from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import User, Chat, ChatMessage, MessageRole
from ...schemas import AgentActionRequest, AgentActionResponse, Module as ModuleSchema, ChatMessage as ChatMessageSchema
from ...auth import get_current_user
from ...agent import process_agent_action

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
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
    else:
        # Create new chat if module_id is provided
        chat = Chat(
            user_id=current_user.id,
            module_id=request.module_id
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
    agent_response_content = f"I processed your request."
    if result["decision"].get("reasoning"):
        agent_response_content += f" {result['decision']['reasoning']}"
    if result.get("web_search_performed"):
        agent_response_content += " I performed a web search to ensure accuracy."
    if result.get("updated_module"):
        agent_response_content += " I've updated the module content."
    
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

