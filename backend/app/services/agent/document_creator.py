"""
Document Creator

Handles document creation operations with name extraction and validation.
"""
from typing import Dict, Any, Optional, List
from opentelemetry import trace
from ...models import Project
from ...schemas import DocumentCreate
from ...exceptions import ValidationError
from ...core.telemetry import get_tracer
from ..document_validator import DocumentValidator
from .name_extractor import DocumentNameExtractor
import logging

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DocumentCreator:
    """Handles document creation operations with name extraction and validation"""
    
    def __init__(self, document_service, document_repo, llm_service, web_search_service):
        self.document_service = document_service
        self.document_repo = document_repo
        self.llm_service = llm_service
        self.web_search_service = web_search_service
        self.name_extractor = DocumentNameExtractor()
    
    async def create_document(
        self,
        decision: Dict[str, Any],
        user_id: int,
        project_id: int,
        user_message: str,
        documents_list: List[Dict],
        project: Optional[Project],
        span: trace.Span
    ) -> tuple[Optional[Dict[str, Any]], Optional[Any]]:
        """
        Create document with name extraction, validation, and web search if needed.
        Returns: (Created document dict or None, WebSearchResult object or None)
        """
        # Extract document name
        document_name = self.name_extractor.extract_name(decision, user_message, documents_list)
        logger.info(f"Creating document with name: '{document_name}'")
        
        # Get initial content if provided in decision
        initial_content = decision.get("document_content") or ""
        
        # Validate document name and content before creation
        validation_result = DocumentValidator.validate_create(
            document_name=document_name,
            content=initial_content
        )
        
        if not validation_result.is_valid:
            logger.warning(f"Document creation validation failed: {validation_result.errors}")
            decision['creation_error'] = {
                'type': 'validation',
                'message': f"Document creation validation failed: {', '.join(validation_result.errors)}"
            }
            return None, None
        
        # Perform web search if needed for document creation
        web_search_result_obj_create = None
        if decision.get("needs_web_search") and decision.get("search_query"):
            logger.info(f"Performing web search for document creation: {decision['search_query']}")
            with tracer.start_as_current_span("agent.web_search_for_create") as web_span:
                web_span.set_attribute("web_search.query", decision["search_query"])
                
                web_search_result_obj_create = await self.web_search_service.search_with_retry(
                    initial_query=decision["search_query"],
                    user_message=user_message,
                    context=f"Project: {project.name if project else 'Unknown'}, Creating document: {document_name}"
                )
                
                web_search_results_for_create = web_search_result_obj_create.get_best_results()
                if web_search_results_for_create:
                    initial_content = f"{initial_content}\n\n{web_search_results_for_create}" if initial_content else web_search_results_for_create
                
                web_span.set_attribute("web_search.attempts", len(web_search_result_obj_create.attempts))
                web_span.set_attribute("web_search.was_retried", web_search_result_obj_create.was_retried())
        
        # Create the document
        created_document = await self._perform_creation(
            document_name,
            initial_content,
            decision,
            user_id,
            project_id,
            documents_list,
            span
        )
        
        return created_document, web_search_result_obj_create
    
    async def _perform_creation(
        self,
        document_name: str,
        initial_content: str,
        decision: Dict[str, Any],
        user_id: int,
        project_id: int,
        documents_list: List[Dict],
        span: trace.Span
    ) -> Optional[Dict[str, Any]]:
        """Perform the actual document creation"""
        try:
            if not self.document_service:
                logger.warning("DocumentService not available, cannot create document")
                return None
            
            created_document_obj = self.document_service.create_document(
                user_id=user_id,
                project_id=project_id,
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
            return created_document
            
        except ValidationError as ve:
            # Handle validation errors (e.g., duplicate document name)
            error_message = str(ve)
            logger.warning(f"Document creation validation error: {error_message}")
            span.record_exception(ve)
            
            # Check if it's a duplicate name error
            if "already exists" in error_message.lower():
                existing_doc = None
                for doc in documents_list:
                    if doc.get('name', '').lower() == document_name.lower():
                        existing_doc = doc
                        break
                decision['creation_error'] = {
                    'type': 'duplicate_name',
                    'message': error_message,
                    'document_name': document_name,
                    'existing_document_id': existing_doc.get('id') if existing_doc else None
                }
            else:
                decision['creation_error'] = {
                    'type': 'validation',
                    'message': error_message
                }
            return None
            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            span.record_exception(e)
            decision['creation_error'] = {
                'type': 'unknown',
                'message': str(e)
            }
            return None

