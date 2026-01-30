"""
Agent Response Formatter

Handles agent response formatting based on decision type and results.
"""
from typing import Dict, Any, Optional, List
from ...schemas import AgentActionRequest
from ...repositories import DocumentRepository
from ..llm_service import LLMService
import logging

logger = logging.getLogger(__name__)


class AgentResponseFormatter:
    """Handles agent response formatting based on decision type and results"""
    
    def __init__(self, llm_service: LLMService, document_repo: DocumentRepository):
        self.llm_service = llm_service
        self.document_repo = document_repo
    
    async def format_response(
        self,
        result: Dict[str, Any],
        request: AgentActionRequest,
        chat: Any,
        chat_history_for_llm: List[Dict]
    ) -> str:
        """
        Format agent response based on decision type.
        Returns: Formatted response string
        """
        decision = result["decision"]
        action = decision.get("action", "ANSWER_ONLY")
        should_edit = decision.get("should_edit", False)
        should_create = decision.get("should_create", False)
        needs_clarification = decision.get("needs_clarification", False)
        pending_confirmation = decision.get("pending_confirmation", False)
        conversational_response = decision.get("conversational_response")
        
        # Log response formatting details
        logger.info(f"→ Response Formatting: action={action}")
        
        # Determine which formatter will be used
        if action == "SHOW_DOCUMENT":
            logger.info(f"  └─ Using: SHOW_DOCUMENT formatter")
        elif action == "LIST_DOCUMENTS":
            logger.info(f"  └─ Using: LIST_DOCUMENTS formatter")
        elif action == "ANSWER_ONLY":
            logger.info(f"  └─ Using: Conversational formatter")
        elif action == "UPDATE_DOCUMENT":
            logger.info(f"  └─ Using: Edit response formatter")
        elif action == "CREATE_DOCUMENT":
            logger.info(f"  └─ Using: Create response formatter")
        elif action == "NEEDS_CLARIFICATION":
            logger.info(f"  └─ Using: Clarification formatter")
        
        # Log additional context
        if result.get('updated_document'):
            logger.info(f"    └─ Document updated: doc_id={result.get('updated_document', {}).get('id', 'N/A')}")
        if result.get('created_document'):
            logger.info(f"    └─ Document created: doc_id={result.get('created_document', {}).get('id', 'N/A')}")
        if result.get('web_search_performed'):
            logger.info(f"    └─ Web search performed: {len(result.get('web_search_results', '')) if result.get('web_search_results') else 0} chars")
        
        # Format based on action type (new format) or decision type (legacy)
        if action == "NEEDS_CLARIFICATION" or needs_clarification:
            return self._format_clarification_response(decision)
        elif pending_confirmation:
            return self._format_confirmation_response(decision)
        elif action == "DELETE_DOCUMENT" or decision.get("should_delete"):
            return self._format_delete_response(result, decision)
        elif action == "CREATE_DOCUMENT" or should_create:
            return self._format_create_response(result, decision)
        elif action == "UPDATE_DOCUMENT" or should_edit:
            return self._format_edit_response(result, decision)
        elif action == "SHOW_DOCUMENT":
            return self._format_show_document_response(result, decision)
        elif action == "LIST_DOCUMENTS":
            return self._format_list_documents_response(result, decision)
        else:
            # ANSWER_ONLY or legacy conversation
            return await self._format_conversational_response(
                result, request, chat, chat_history_for_llm, conversational_response
            )
    
    def _format_clarification_response(self, decision: Dict[str, Any]) -> str:
        """Format clarification request response"""
        clarification_question = decision.get("clarification_question")
        return clarification_question or "Could you please provide more details about what you'd like me to do?"
    
    def _format_confirmation_response(self, decision: Dict[str, Any]) -> str:
        """Format confirmation request response"""
        confirmation_prompt = decision.get("confirmation_prompt")
        return confirmation_prompt or "This action requires confirmation. Should I proceed?"
    
    def _format_create_response(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format document creation response (success or failure)"""
        if result.get("created_document"):
            return self._format_create_success(result, decision)
        else:
            return self._format_create_failure(result, decision)
    
    def _format_create_success(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format successful document creation response"""
        created_doc = result["created_document"]
        intent_statement = decision.get("intent_statement")
        parts = []
        
        # Part 1: Action summary (what was done) - use past tense
        if intent_statement:
            intent = intent_statement.replace("I'll create", "I've created").replace("I will create", "I've created")
            parts.append(intent)
        else:
            parts.append(f"I've created the document '{created_doc['name']}' in this project.")
        
        # Part 2: Content summary (what's in the document)
        content_summary = decision.get("content_summary")
        if content_summary:
            parts.append(f"\n\n**Document Content Summary:**\n{content_summary}")
        elif decision.get("document_content"):
            doc_content = decision.get("document_content", "")
            if doc_content:
                preview = doc_content[:200] + "..." if len(doc_content) > 200 else doc_content
                parts.append(f"\n\n**Initial Content Preview:**\n{preview}")
        
        # Part 3: Web search details (if applicable)
        parts.extend(self._format_web_search_details(result.get("web_search_result")))
        
        return "\n".join(parts)
    
    def _format_create_failure(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format failed document creation response"""
        parts = []
        creation_error = decision.get('creation_error', {})
        error_type = creation_error.get('type', 'unknown')
        intent_statement = decision.get("intent_statement")
        
        if error_type == 'duplicate_name':
            existing_doc_id = creation_error.get('existing_document_id')
            document_name = creation_error.get('document_name', decision.get('document_name', 'Unknown'))
            
            parts.append(f"A document named '{document_name}' already exists in this project.")
            if existing_doc_id:
                parts.append(f"I can add this content to the existing document instead. Would you like me to update '{document_name}' with the new content?")
            else:
                parts.append("Would you like me to:")
            parts.append("1. Add this content to the existing document")
            parts.append("2. Create a new document with a different name")
            
            if intent_statement:
                parts.append(f"\n\nOriginal intent: {intent_statement}")
        else:
            # Other validation or unknown errors
            error_msg = creation_error.get('message', 'Unknown error')
            
            if error_type == 'validation':
                parts.append(f"I tried to create the document but validation found issues:")
                parts.append(f"- {error_msg}")
                parts.append("\nPlease fix these issues and try again.")
            elif not decision.get("document_name"):
                parts.append("I cannot create a document without a name.")
                parts.append("Please specify a name, like 'Create a document called Recipes'.")
            else:
                document_name = decision.get('document_name', 'Unknown')
                parts.append(f"I attempted to create a document called '{document_name}', but it wasn't created successfully.")
                if error_msg and error_msg != 'Unknown error':
                    parts.append(f"\n**Error:** {error_msg}")
                    parts.append("\nPlease check the document name or try again with a different name.")
                else:
                    parts.append("\nPlease try again or check if a document with that name already exists.")
            
            if intent_statement:
                parts.append(f"\n\n**Original intent:** {intent_statement}")
        
        return "\n".join(parts)
    
    def _format_edit_response(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format document edit response (success or failure)"""
        if result.get("updated_document"):
            return self._format_edit_success(result, decision)
        else:
            return self._format_edit_failure(result, decision)
    
    def _format_edit_success(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format successful document edit response"""
        parts = []
        intent_statement = decision.get("intent_statement")
        change_summary = decision.get("change_summary")
        
        # Part 1: Action summary (what was done)
        if intent_statement:
            parts.append(intent_statement)
        
        # Log response building details
        logger.info(f"Building edit response: intent_statement={'present' if intent_statement else 'missing'}, "
                    f"content_summary={'present' if decision.get('content_summary') else 'missing'}, "
                    f"change_summary={'present' if change_summary else 'missing'}, "
                    f"web_search_result={'present' if result.get('web_search_result') else 'missing'}, "
                    f"web_search_attempts={len(result.get('web_search_result').attempts) if result.get('web_search_result') else 0}")
        
        # Part 2: Content summary (what actually changed/added)
        content_summary = decision.get("content_summary")
        if content_summary:
            parts.append(f"\n\n**Content Summary:**\n{content_summary}")
        elif change_summary:
            parts.append(f"\n\n**Changes:** {change_summary}")
        
        # Part 3: Validation warnings (if any)
        validation_warnings = decision.get("validation_warnings")
        if validation_warnings:
            parts.append(f"\n\n**Note:** {', '.join(validation_warnings)}")
        
        # Part 4: Web search details (if applicable)
        parts.extend(self._format_web_search_details(result.get("web_search_result")))
        
        # Join all parts with newlines for better readability in chat
        if parts:
            return "\n".join(parts)
        else:
            return "I've updated the document content."
    
    def _format_edit_failure(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format failed document edit response"""
        parts = []
        validation_errors = decision.get("validation_errors")
        
        if validation_errors:
            parts.append("I rewrote the document but validation found issues:")
            for error in validation_errors:
                parts.append(f"- {error}")
            parts.append("\nI can retry with fixes. Should I proceed?")
        else:
            parts.append("I understood your request, but couldn't update the document.")
            if decision.get("reasoning"):
                parts.append(f"Reason: {decision['reasoning']}")
            else:
                parts.append("The document may not exist or there was an error. Please check the document ID or try again.")
        
        return "\n".join(parts)
    
    def _format_delete_response(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format document deletion response (success or failure)"""
        if result.get("deleted_document"):
            return self._format_delete_success(result, decision)
        else:
            return self._format_delete_failure(result, decision)
    
    def _format_delete_success(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format successful document deletion response"""
        deleted_doc = result.get("deleted_document", {})
        doc_name = deleted_doc.get("name", "the document")
        
        intent_statement = decision.get("intent_statement")
        if intent_statement:
            # Use intent_statement if it's in first person past tense
            if intent_statement.startswith("I have") or intent_statement.startswith("I've"):
                return intent_statement
            # Otherwise, format it
            return f"I have deleted {doc_name}."
        else:
            return f"I have deleted {doc_name}."
    
    def _format_delete_failure(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format failed document deletion response"""
        return "I couldn't delete the document. It may not exist or you may not have permission to delete it."
    
    def _format_web_search_details(self, web_search_result: Optional[Any]) -> List[str]:
        """Format web search details section"""
        parts = []
        if web_search_result and web_search_result.attempts:
            parts.append("\n\n**Web Search Details:**")
            for attempt in web_search_result.attempts:
                parts.append(f"\n**Search Query {attempt.attempt_number}:** `{attempt.query}`")
                if attempt.summary:
                    parts.append(f"**Results Summary:** {attempt.summary}")
                if attempt.quality_score is not None:
                    parts.append(f"**Quality Score:** {attempt.quality_score:.2f}/1.0")
                if attempt.retry_reason:
                    parts.append(f"**Retry Reason:** {attempt.retry_reason}")
                if attempt.attempt_number < len(web_search_result.attempts):
                    parts.append("")  # Add spacing between attempts
        return parts
    
    async def _format_conversational_response(
        self,
        result: Dict[str, Any],
        request: AgentActionRequest,
        chat: Any,
        chat_history_for_llm: List[Dict],
        conversational_response: Optional[str]
    ) -> str:
        """Format conversational response for questions/general conversation"""
        # CRITICAL: If web search was performed, always generate response to include results and post-processing
        web_search_performed = result.get("web_search_performed", False)
        if conversational_response and not web_search_performed:
            return conversational_response
        
        # Generate a conversational response for questions/general conversation
        logger.debug("Generating conversational response" + (" (web search performed, overriding decision's conversational_response)" if conversational_response and web_search_performed else ""))
        
        # Get project documents for context if user is asking about content
        project_id_to_check = request.project_id or chat.project_id
        project_documents_content = None
        if project_id_to_check:
            project_documents = self.document_repo.get_by_project_id(project_id_to_check)
            if project_documents:
                project_documents_content = "\n\n".join([
                    f"Document: {d.name}\nContent: {d.content[:500]}..." if len(d.content) > 500 else f"Document: {d.name}\nContent: {d.content}"
                    for d in project_documents
                ])
        
        # Build context with document content if available and user is asking for info
        context = result.get("decision", {}).get("reasoning", "")
        user_message_lower = request.message.lower()
        
        # Check if user is asking about location/status of documents
        is_location_question = any(keyword in user_message_lower for keyword in ["where", "where did", "where is", "where are", "what did you", "what did i"])
        
        if project_documents_content and any(keyword in user_message_lower for keyword in ["summarize", "read", "tell me about", "what's in", "show me", "describe", "where", "where did", "where is"]):
            context = f"Project documents:\n{project_documents_content}\n\n{context if context else 'User is asking about the project documents.'}"
        
        # For location questions, extract recent document operations from chat history
        if is_location_question and chat_history_for_llm:
            recent_operations = []
            for msg in reversed(chat_history_for_llm[-5:]):
                role = msg.get("role", "")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                
                if role in ["assistant", "system"]:
                    content = msg.get("content", "")
                    metadata = msg.get("metadata", {})
                    decision = metadata.get("decision", {})
                    
                    if decision.get("should_create") or decision.get("should_edit"):
                        doc_name = decision.get("document_name") or "a document"
                        doc_id = decision.get("document_id")
                        action = "created" if decision.get("should_create") else "updated"
                        intent = decision.get("intent_statement", f"I {action} {doc_name}")
                        
                        if doc_id:
                            try:
                                doc = self.document_repo.get_by_id(doc_id)
                                if doc:
                                    doc_name = doc.name
                            except Exception:
                                pass
                        
                        recent_operations.append(f"- {intent} (Document: {doc_name})")
            
            if recent_operations:
                context = f"Recent document operations from conversation history:\n" + "\n".join(recent_operations[:3]) + "\n\n" + context
        
        # Include web search results if available for conversational responses
        web_search_results_for_conversation = result.get("web_search_results")
        
        logger.info(f"[AGENT] Preparing conversational response: "
                   f"has_results={web_search_results_for_conversation is not None}, "
                   f"results_length={len(web_search_results_for_conversation) if web_search_results_for_conversation else 0}, "
                   f"result_keys={list(result.keys())}, "
                   f"web_search_performed={web_search_performed}, "
                   f"conversational_response_from_decision={'present' if conversational_response else 'missing'}")
        
        if web_search_results_for_conversation:
            logger.info(f"[AGENT] Web search results preview (first 500 chars): {web_search_results_for_conversation[:500]}")
        
        agent_response_content = await self.llm_service.generate_conversational_response(
            request.message,
            context,
            chat_history=chat_history_for_llm,
            web_search_results=web_search_results_for_conversation
        )
        
        logger.info(f"[AGENT] Conversational response received, length: {len(agent_response_content)}, preview: {agent_response_content[:200]}")
        return agent_response_content
    
    def _format_show_document_response(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format response for showing document content"""
        target_documents = decision.get("target_documents", [])
        parts = []
        
        if not target_documents:
            return "I couldn't find the document you're asking about."
        
        for doc in target_documents:
            doc_name = doc.get("name", "Unknown")
            doc_content = doc.get("content", "")
            
            parts.append(f"**{doc_name}**")
            if doc_content:
                # Show full content or summary based on length
                if len(doc_content) > 2000:
                    parts.append(f"\n{doc_content[:1500]}...\n\n[Document continues - {len(doc_content)} characters total]")
                else:
                    parts.append(f"\n{doc_content}")
            else:
                parts.append("\n(Empty document)")
            parts.append("")  # Add spacing between documents
        
        return "\n".join(parts)
    
    def _format_list_documents_response(self, result: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Format response for listing documents"""
        documents_list = decision.get("documents_list", [])
        parts = []
        
        if not documents_list:
            parts.append("You don't have any documents in this project yet.")
        else:
            parts.append(f"You have {len(documents_list)} document(s) in this project:\n")
            for i, doc in enumerate(documents_list, 1):
                doc_name = doc.get("name", "Unnamed")
                content_length = doc.get("content_length", 0)
                parts.append(f"{i}. **{doc_name}** ({content_length:,} characters)")
        
        return "\n".join(parts)

