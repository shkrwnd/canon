from fastapi import APIRouter, Depends
from ...core.security import get_current_user
from ...models import User
from ...schemas import AgentActionRequest, AgentActionResponse
from ...services import AgentService, ChatService
from ..dependencies import get_agent_service, get_chat_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/act", response_model=AgentActionResponse)
async def agent_action(
    request: AgentActionRequest,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Process agent action: detect intent, edit modules, perform web search.
    
    This endpoint handles the complete agent workflow including:
    - Chat management (creation/retrieval)
    - Message storage
    - Agent decision making
    - Module updates
    - Response generation
    """
    return await agent_service.process_agent_action_with_chat(
        user_id=current_user.id,
        request=request,
        chat_service=chat_service
    )
