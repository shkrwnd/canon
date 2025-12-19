from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..repositories import ModuleRepository, ChatRepository
from ..models import Module
from .llm_service import LLMService
from ..clients import LLMProviderFactory, search_web
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Service for agent operations"""
    
    def __init__(self, db: Session, llm_service: Optional[LLMService] = None):
        """
        Initialize agent service
        
        Args:
            db: Database session
            llm_service: Optional LLM service. If None, creates default from config.
        """
        self.module_repo = ModuleRepository(db)
        self.chat_repo = ChatRepository(db)
        self.db = db
        # Use provided service or create default
        if llm_service is None:
            provider = LLMProviderFactory.create_provider()
            llm_service = LLMService(provider)
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
