from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from .models import Module
from .openai_client import get_agent_decision, rewrite_module_content
from .tavily_client import search_web


async def process_agent_action(
    db: Session,
    user_id: int,
    user_message: str,
    module_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process agent action: detect intent, decide on edits, perform web search if needed,
    and rewrite module content.
    """
    # Get all user modules
    user_modules = db.query(Module).filter(Module.user_id == user_id).all()
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
        module = db.query(Module).filter(Module.id == module_id, Module.user_id == user_id).first()
        if module:
            current_module = {
                "id": module.id,
                "name": module.name,
                "standing_instruction": module.standing_instruction,
                "content": module.content
            }
    
    # Get agent decision
    decision = await get_agent_decision(user_message, modules_list, current_module)
    
    web_search_performed = False
    web_search_results = None
    
    # Perform web search if needed
    if decision.get("needs_web_search") and decision.get("search_query"):
        web_search_results = search_web(decision["search_query"])
        web_search_performed = True
    
    # Rewrite module if decision says so
    updated_module = None
    if decision.get("should_edit") and decision.get("module_id"):
        target_module_id = decision["module_id"]
        target_module = db.query(Module).filter(
            Module.id == target_module_id,
            Module.user_id == user_id
        ).first()
        
        if target_module:
            # Rewrite the entire module content
            new_content = await rewrite_module_content(
                user_message=user_message,
                standing_instruction=target_module.standing_instruction,
                current_content=target_module.content,
                web_search_results=web_search_results
            )
            
            # Update module
            target_module.content = new_content
            db.commit()
            db.refresh(target_module)
            
            updated_module = {
                "id": target_module.id,
                "name": target_module.name,
                "standing_instruction": target_module.standing_instruction,
                "content": target_module.content,
                "user_id": target_module.user_id,
                "created_at": target_module.created_at,
                "updated_at": target_module.updated_at
            }
    
    return {
        "decision": decision,
        "updated_module": updated_module,
        "web_search_performed": web_search_performed,
        "web_search_results": web_search_results if web_search_performed else None
    }



