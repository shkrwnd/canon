from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

# Load examples from separate file
try:
    from ..prompts.examples import PROMPT_EXAMPLES
except ImportError:
    logger.warning("Could not load prompt examples - using empty string")
    PROMPT_EXAMPLES = ""


class PromptService:
    """Service for prompt engineering with two-stage prompting and dynamic construction"""
    
    @staticmethod
    def _extract_document_summary_smart(content: str, name: str, standing_instruction: str = "") -> str:
        """
        Smart extraction: combines multiple signals to understand document content.
        Uses headings, standing instructions, and content structure - no LLM needed.
        """
        if not content:
            return "Empty document"
        
        signals = []
        
        # Signal 1: Standing instruction (explicit purpose)
        if standing_instruction:
            signals.append(f"Purpose: {standing_instruction[:100]}")
        
        # Signal 2: Document headings (structure)
        from .document_validator import DocumentValidator
        headings = DocumentValidator.extract_headings(content)
        if headings:
            # Group by heading level to understand hierarchy
            h1_h2 = headings[:4]  # First 4 headings
            if h1_h2:
                signals.append(f"Main sections: {', '.join(h1_h2)}")
        
        # Signal 3: First paragraph (introduction/overview)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip() and len(p.strip()) > 50]
        if paragraphs:
            intro = paragraphs[0]
            # Clean markdown
            intro = re.sub(r'^#{1,6}\s+', '', intro, flags=re.MULTILINE)
            intro = re.sub(r'\*\*([^*]+)\*\*', r'\1', intro)
            intro = re.sub(r'\*([^*]+)\*', r'\1', intro)
            if len(intro) > 150:
                intro = intro[:150] + "..."
            signals.append(intro)
        
        # Signal 4: Content type indicators
        content_lower = content.lower()
        type_indicators = []
        if 'recipe' in content_lower or 'ingredient' in content_lower:
            type_indicators.append("recipes")
        if '```' in content or 'def ' in content or 'class ' in content:
            type_indicators.append("code")
        if 'http' in content_lower or 'www.' in content_lower:
            type_indicators.append("links/references")
        if type_indicators:
            signals.append(f"Contains: {', '.join(type_indicators)}")
        
        # Signal 5: Document length (indicates scope)
        if len(content) > 5000:
            signals.append("Large document (comprehensive)")
        elif len(content) < 200:
            signals.append("Short note")
        
        # Combine signals
        if signals:
            return " | ".join(signals[:3])  # Use top 3 signals
        else:
            return content[:100].replace('\n', ' ') + "..."  # Fallback
    
    @staticmethod
    def _build_documents_with_summaries(documents: list) -> str:
        """
        Build document list with names and intelligent summaries for semantic matching.
        Uses headings, standing instructions, and content structure.
        """
        if not documents:
            return "No documents available"
        
        docs = []
        for d in documents[:15]:  # Limit to 15 documents for prompt size
            name = d.get('name', 'Unnamed')
            content = d.get('content', '')
            standing_instruction = d.get('standing_instruction', '')
            
            summary = PromptService._extract_document_summary_smart(
                content,
                name,
                standing_instruction
            )
            docs.append(f"  - \"{name}\": {summary}")
        
        return "Available documents:\n" + "\n".join(docs)
    
    @staticmethod
    def _build_compressed_documents_list(documents: list) -> str:
        """Build compressed document list for prompts"""
        if not documents:
            return "No documents available"
        
        docs = []
        for d in documents:
            content = d.get('content', '')
            name = d['name']
            doc_id = d['id']
            
            # Compressed content preview
            if len(content) <= 2000:
                preview = content if content else '(empty)'
            else:
                preview = f"{content[:1500]}\n[...{len(content)-2000} chars...]\n{content[-500]}"
            
            docs.append(f"Doc: {name} (id:{doc_id})\n{preview}\n---")
        
        return "\n".join(docs)
    
    @staticmethod
    def classify_intent_rule_based(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Original rule-based intent classification.
        Kept for backward compatibility and as fallback.
        """
        project_info = ""
        if project_context:
            description = project_context.get('description') or ''
            description_preview = description[:100] if description else ''
            project_info = f"Project: {project_context.get('name', 'Unknown')} - {description_preview}"
        
        doc_names = [d['name'] for d in documents[:5]] if documents else []
        doc_list = ", ".join(doc_names) if doc_names else "None"
        
        # Build conversation context from recent messages
        conversation_context = ""
        if chat_history:
            recent_messages = chat_history[-5:]  # Last 5 messages for context
            conversation_context = "\n\nRecent conversation:\n"
            for msg in recent_messages:
                role = msg.get("role", "user")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                content = msg.get("content", "")
                # Include pending confirmation context if present
                if msg.get("pending_confirmation"):
                    intent = msg.get("intent_statement", "")
                    conversation_context += f"{role}: {content} [PENDING CONFIRMATION: {intent}]\n"
                else:
                    conversation_context += f"{role}: {content}\n"
        
        prompt = f"""Classify user intent. Respond with JSON only.

Context:
{project_info}
Documents: {doc_list}
{conversation_context}
User: "{user_message}"

Intent types:
- "conversation": Questions, greetings, info requests (no document action)
  Examples: "what is", "who is", "tell me about", "how do I", "explain", "where did", "where is", "where are"
  CRITICAL: Understand the user's INTENT:
    * Pure questions (seeking information, no action requested) → conversation
      Examples: "who is the current president", "what is Python", "when did X happen"
      These are just questions - user wants an answer, not a document action
    * Questions disguised as actions (user wants you to DO something) → edit/create
      Examples: "add X to document" (action word + document reference)
      These contain action words AND reference documents - user wants an action
  CRITICAL: If user asks a general knowledge question with NO document mentioned → conversation
  CRITICAL: Questions are ALWAYS conversation UNLESS they explicitly mention a document AND contain action words
  Examples of questions: "where did you make the changes", "what did you create", "how do I save", "where is the script", "who is the current president"
  
- "edit": Modify existing doc (action words: add, update, change, remove, edit, delete, save, put)
  Examples: "add X", "update Y", "save it", "save that", "put this in", "change Z"
  CRITICAL: "save it" or "save that" = edit (save content to document)
  CRITICAL: "Edit [document] and add/update/change [X]" = edit (e.g., "Edit the Python guide and add latest version")
  CRITICAL: "edit the document about [topic]" = edit (e.g., "edit the document about the latest Python features")
  CRITICAL: "edit the document called [name]" = edit (e.g., "edit the document called NonExistentDoc")
  CRITICAL: "Add [X] to [document]" = edit (e.g., "Add hotels to the itinerary")
  CRITICAL: If message starts with "edit" or "Edit" → ALWAYS classify as "edit" (even if document name is vague or doesn't exist)
  NOT questions: "where did you save" = conversation (question), not edit
  CONFIRMATION: If recent conversation shows agent asked for confirmation (e.g., "Should I proceed?", "Shall I make the changes?") and user says "yes"/"ok"/"proceed"/"go ahead"/"sure" → edit
  
- "create": Create new doc (words: create, make, new document, script, outline, plan)
  Examples: "create a script", "create a [thing]", "make a new [thing]", "write a script"
  CRITICAL: "create a script" or "create a [noun]" = create (new document)
  CRITICAL: "make a new document" or "make a new [thing]" = create (ALWAYS, even if similar document exists)
  CRITICAL: "new document" keywords take priority over content matching - if user says "make a new document", it's create, not edit
  NOT questions: "where did you create" = conversation (question), not create
  CONFIRMATION: If recent conversation shows agent asked for confirmation about creating and user says "yes"/"ok"/"proceed"/"go ahead"/"sure" → create
  
- "clarify": Vague/ambiguous (needs more info)
  Examples: "do something", "fix it" (unclear what)

Key patterns:
- Pure questions (no document mentioned, no action words) → conversation (ALWAYS)
  Examples: "who is the current president", "what is the capital of France", "when did X happen"
  These are information-seeking questions with no document context
- Questions (what/where/when/how/why/who/did you/is it/are you) → conversation (ALWAYS, unless document + action word)
  If question mentions a document AND has action words → check if it's an action request
- "create a [noun]" → create (e.g., "create a script", "create a plan")
- "make a new document" or "make a new [thing]" → create (ALWAYS, prioritize over content matching)
- "save it/that/this" → edit (save content to document)
- "add/update/change [content]" → edit (if document context exists)
- "Edit [document] and add/update/change [X]" → edit (ALWAYS, document name is mentioned)
- "edit the document about [topic]" → edit (ALWAYS, even if document name is vague)
- "edit the document called [name]" → edit (ALWAYS, even if document doesn't exist)
- "Add [X] to [document]" → edit (ALWAYS, document name is explicitly mentioned)
- Confirmation responses ("yes", "ok", "proceed", "go ahead", "sure", "yeah", "yep") → Check recent conversation:
  * If agent asked "Should I proceed with [edit/change/update]?" or similar → edit
  * If agent asked "Should I create [document]?" or similar → create
  * If recent message shows [PENDING CONFIRMATION] with should_edit → edit
  * If recent message shows [PENDING CONFIRMATION] with should_create → create
  * If no clear action in context → conversation

Response JSON:
{{
    "intent_type": "conversation"|"edit"|"create"|"clarify",
    "confidence": 0.0-1.0,
    "needs_documents": boolean  // true if need full doc content for decision
}}"""
        
        return prompt
    
    @staticmethod
    def classify_intent_contextual(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Contextual intent classification - simpler, more natural prompt that trusts LLM understanding.
        Uses hybrid approach: last N messages + original intent search.
        """
        from ..config import settings
        
        project_info = ""
        if project_context:
            description = project_context.get('description') or ''
            description_preview = description[:100] if description else ''
            project_info = f"Project: {project_context.get('name', 'Unknown')} - {description_preview}"
        
        doc_names = [d['name'] for d in documents[:5]] if documents else []
        doc_list = ", ".join(doc_names) if doc_names else "None"
        
        # Get history window from settings (default 20)
        history_window = getattr(settings, 'intent_classification_history_window', 20)
        
        # Build conversation context - hybrid approach
        conversation_context = ""
        if chat_history:
            # Use last N messages for recent context
            recent_messages = chat_history[-history_window:]
            
            # Search for original create/edit intent in full history (from most recent backwards)
            original_intent_message = None
            original_intent_type = None
            for msg in reversed(chat_history):
                role = msg.get("role", "user")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                
                if role == "user" or role == "USER":
                    content = msg.get("content", "")
                    content_lower = content.lower()
                    
                    # Check for create intent
                    if any(word in content_lower for word in ["create", "make a new", "write a", "new document"]):
                        original_intent_message = msg
                        original_intent_type = "create"
                        break
                    # Check for edit intent
                    elif any(word in content_lower for word in ["edit", "add", "update", "change", "save"]):
                        original_intent_message = msg
                        original_intent_type = "edit"
                        break
            
            conversation_context = "\n\nCONVERSATION HISTORY:\n"
            
            # Include original intent message if found and not already in recent messages
            if original_intent_message:
                original_in_recent = any(
                    msg.get("content") == original_intent_message.get("content")
                    for msg in recent_messages
                )
                
                if not original_in_recent:
                    content = original_intent_message.get("content", "")
                    # Find position in history
                    original_index = next(
                        (i for i, msg in enumerate(chat_history) if msg == original_intent_message),
                        -1
                    )
                    messages_ago = len(chat_history) - original_index if original_index >= 0 else "unknown"
                    conversation_context += f"user: {content} [ORIGINAL {original_intent_type.upper()} REQUEST - {messages_ago} messages ago]\n"
                    conversation_context += "...\n"  # Indicate gap in messages
            
            # Then include recent messages
            for msg in recent_messages:
                role = msg.get("role", "user")
                if hasattr(role, 'value'):
                    role = role.value
                elif not isinstance(role, str):
                    role = str(role).lower()
                content = msg.get("content", "")
                
                # Include pending confirmation context if present
                if msg.get("pending_confirmation"):
                    intent = msg.get("intent_statement", "")
                    conversation_context += f"{role}: {content} [PENDING CONFIRMATION: {intent}]\n"
                else:
                    conversation_context += f"{role}: {content}\n"
        else:
            conversation_context = "\n\nCONVERSATION HISTORY: No previous messages\n"
        
        prompt = f"""Classify the user's intent based on their message and the conversation context.

{conversation_context}

CURRENT MESSAGE: "{user_message}"

PROJECT CONTEXT:
{project_info}
{doc_list}

=== CORE DECISION PRINCIPLE ===
**PRIMARY RULE**: If message has explicit action verbs (add, update, create, edit, make, save) requesting document operations → UPDATE_DOCUMENT/CREATE_DOCUMENT
**PRIMARY RULE**: If message seeks information, provides context, or has no action verbs → ANSWER_ONLY
**PRIMARY RULE**: If message is ambiguous → lower confidence (< 0.6) or NEEDS_CLARIFICATION

=== ACTION TYPES ===
- UPDATE_DOCUMENT: Explicit action verbs (add, update, change, edit, delete, save, put, implement, apply) + document reference
  * Special: "save it/that/this" → save content from conversation to document
  * Must contain explicit action verbs requesting document modification
  * Questions seeking information are NOT actions
  
- CREATE_DOCUMENT: Explicit action verbs (create, make, new document, write) + new document intent
  * "create a [noun]" → create new document
  
- ANSWER_ONLY: Questions, statements providing context, no action verbs requesting document operations
  * Questions: "what/how/which/why/could/would/should" seeking information
  * Context statements: User states facts, shares information without action verbs
  * Personal/emotional/casual: "i am feeling sad", "how are you", "good morning" → empty targets []
  * Follow-up questions seeking information = ANSWER_ONLY
  * Messages unrelated to documents → empty targets []
  
- SHOW_DOCUMENT: "show me [document]", "read [document]", "what's in [document]", "summarize [document]"
  
- LIST_DOCUMENTS: "list documents", "show all documents", "what documents do I have"
  
- NEEDS_CLARIFICATION: Too vague, confidence < 0.5, "do something", "fix it" (unclear what)

=== KEY RULES ===
1. **Statements without action verbs = ANSWER_ONLY** (providing context, not requesting action)
2. **Do NOT infer document operations from conversation history** - only act on explicit requests
3. **Content alignment**: Only match documents if request topic aligns with document topic (unless user explicitly names document)
4. **If misaligned and no explicit name → CREATE_DOCUMENT** instead of UPDATE_DOCUMENT
5. **intent_statement must describe CURRENT message only**, not previous messages
6. **Use history to resolve ambiguity** (e.g., "it" refers to what?) but extract intent from current message
7. **If statement is ambiguous** (could be context or action) → lower confidence (< 0.6) or NEEDS_CLARIFICATION

=== EDGE CASES ===
- Questions about past actions ("where did you", "what did you") = ANSWER_ONLY
- Message contains "here" or "in chat" = SHOW_DOCUMENT or ANSWER_ONLY
- Pure questions without action words = ANSWER_ONLY
- If user previously mentioned creating/editing, follow-up maintains intent ONLY IF it's an action request

=== DOCUMENT MATCHING ===
- **Content Alignment Check**: Verify request topic matches document topic before matching
  * If misaligned (e.g., "business plan" request vs "skincare routine" document) → DO NOT match, use CREATE_DOCUMENT
  * Exception: If user explicitly names document → match regardless of alignment
- Match by: document name reference, semantic matching (name/summary), topic alignment
- "primary": Main document(s) needed; "secondary": Additional context
- Empty targets [] for: personal statements, casual conversation, unrelated messages
- **Target rules by action**:
  * CREATE_DOCUMENT: empty targets []
  * UPDATE_DOCUMENT: targets contain document to update
  * SHOW_DOCUMENT: targets contain document(s) to show
  * ANSWER_ONLY: targets contain documents that help answer (if any)
  * LIST_DOCUMENTS: empty targets []
  * NEEDS_CLARIFICATION: empty targets []

=== CONFIDENCE SCORING ===
- HIGH (0.8-1.0): Clear, unambiguous requests with explicit intent
- MEDIUM (0.5-0.7): Somewhat ambiguous but reasonable inference possible
- LOW (0.3-0.5): Very ambiguous, unclear intent
- If confidence < 0.5 → strongly consider NEEDS_CLARIFICATION
- Lower confidence for ambiguous statements that could be context or action

Response JSON:
{{
    "action": "UPDATE_DOCUMENT | SHOW_DOCUMENT | CREATE_DOCUMENT | ANSWER_ONLY | LIST_DOCUMENTS | NEEDS_CLARIFICATION",
    "targets": [
        {{
            "document_name": "Python Guide",
            "summary": "Brief description of why this document is relevant (what it contains that matches the user's request)",
            "role": "primary"
        }}
    ],
    "new_document": {{ "name": "optional document name" }},
    "confidence": 0.0-1.0,
    "intent_statement": "What user wants in CURRENT MESSAGE only (use history for context, not for intent)"
      * **CRITICAL**: This must describe the intent of the CURRENT MESSAGE, not previous messages
      * Use chat history to understand context and resolve ambiguity (e.g., "it" refers to what?)
      * But the intent_statement should describe what the user wants NOW, in this specific message
      * **Do NOT** copy intent from previous messages - extract intent from the CURRENT message, even if context helps understand it
}}"""
        
        return prompt
    
    @staticmethod
    def classify_intent(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Intent classification - uses version based on settings.
        Falls back to contextual if version not specified.
        """
        from ..config import settings
        
        prompt_version = getattr(settings, 'intent_classification_prompt_version', 'contextual')
        
        if prompt_version == "contextual":
            return PromptService.classify_intent_contextual(
                user_message, documents, project_context, chat_history
            )
        else:
            # Use original rule-based prompt
            return PromptService.classify_intent_rule_based(
                user_message, documents, project_context, chat_history
            )
    
    @staticmethod
    def get_agent_decision_prompt(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        intent_type: Optional[str] = None,
        intent_metadata: Optional[Dict] = None
    ) -> str:
        """
        Stage 2: Generate detailed decision prompt with dynamic sections
        Only includes relevant sections based on intent_type
        """
        # Get current date information dynamically
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_date_str = now.strftime('%B %d, %Y')
        
        documents_list = PromptService._build_compressed_documents_list(documents)
        
        project_info = ""
        if project_context:
            project_info = f"Project: {project_context.get('name', 'Unknown')} (id:{project_context.get('id')})\n"
        
        # Add structured intent context if available
        intent_context = ""
        if intent_metadata:
            action = intent_metadata.get("action")
            targets = intent_metadata.get("targets", [])
            intent_statement = intent_metadata.get("intent_statement", "")
            
            intent_context = f"""
STAGE 1 CLASSIFICATION:
- Action: {action}
- Intent: {intent_statement}
- Target Documents: {len(targets)} document(s) identified
"""
            if targets:
                primary_target = next((t for t in targets if t.get("role") == "primary"), None)
                if primary_target:
                    intent_context += f"- Primary target: {primary_target.get('document_name')} (id: {primary_target.get('document_id')})\n"
                    if primary_target.get('summary'):
                        intent_context += f"  Summary: {primary_target.get('summary')}\n"
        
        # Core rules (always included)
        core = f"""You're a document maintainer. Keep docs accurate and structured.
{project_info}
{intent_context}
Current Date Context: Today is {current_date_str}, current year is {current_year}

Core Rules:
- Default to CONVERSATION unless explicit action words
- Never edit/create without explicit request
- Check existing docs before creating (match by name)
- Infer from context when possible, don't ask
- Act decisively when info exists
- Use conversation history: "save it" means save content from previous messages

Documents:
{documents_list}

User: "{user_message}"
"""
        
        # Dynamic sections based on intent_type
        sections = []
        
        if intent_type == "conversation":
            # Pre-calculate most recent December year for this section
            most_recent_dec = current_year - 1 if current_month < 12 else current_year
            sections.append(f"""
=== CONVERSATION RESPONSE ===
Provide helpful response:
- General knowledge questions (not about documents): Use web search if needed, provide direct answer
  * "who is the current president" → needs_web_search: true, search_query: "current president of US {current_year}"
  * "what is the capital of France" → needs_web_search: true, search_query: "capital of France"
  * "what are the latest US administration changes in December" → needs_web_search: true, search_query: "US administration changes December {most_recent_dec}" (use most recent December based on current date: {current_date_str})
  * Answer directly based on web search results or your knowledge
  * CRITICAL: When web search results are provided, use SPECIFIC information from the results, not generic/vague answers
  * Include specific names, dates, events, and details from the web search results
  * DO NOT give generic answers like "there were some changes" - provide actual specific information
- **Actionable advice/strategy questions**: Use web search for current, practical advice
  * Semantic patterns that indicate actionable advice requests:
    - Questions asking "what can I do", "what should I do", "how can I", "how do I", "how to"
    - Questions asking "what do [people/group] do" to achieve something
    - Questions asking for strategies, tips, steps, methods, or techniques
    - Questions asking "what works", "what's effective", "best practices"
    - Questions seeking practical, actionable information rather than just factual knowledge
  * **Rule**: If question seeks actionable steps, strategies, tips, or practical advice → needs_web_search: true
  * Generate search_query based on the topic and action requested (e.g., if user asks "what do X do to Y", search for "X strategies to Y" or "how to Y as X")
  * Answer directly based on web search results or your knowledge
  * CRITICAL: When web search results are provided, use SPECIFIC information from the results, not generic/vague answers
  * Include specific names, dates, events, and details from the web search results
  * DO NOT give generic answers like "there were some changes" - provide actual specific information
- Greetings: Include project summary + doc list
- Questions about documents: Answer based on doc content and conversation history
  * "where did you make/create/save" → Tell user which document was created/updated
  * "what did you do" → Explain what action was taken
  * "how do I" → Provide instructions
- "What can you do?": Analyze project, suggest based on gaps
- "Summarize": Provide doc summary in chat (don't edit)
- For location questions: Reference specific document names and what was done
""")
        
        elif intent_type == "edit":
            sections.append("""
=== EDIT REQUEST ===
Action words: add, update, change, remove, edit, rewrite, modify, delete, insert, save, put

**CRITICAL: Content Alignment Validation**
Before deciding to edit an existing document, check if the request aligns with the document's topic:
- Compare the user's request topic with the document's name, summary, and content topic
- If request topic doesn't align with document topic:
  * If user explicitly named the document → proceed with edit (user's explicit choice)
  * If user did NOT explicitly name the document → use CREATE_DOCUMENT instead
  * Example: Request about "business plan" but document is "Skincare Routine" → CREATE_DOCUMENT (unless user said "add to Skincare Routine")
- **Rule**: Only edit existing documents if request topic aligns with document topic OR user explicitly specified the document
- **Rule**: If misaligned and no explicit document name → should_create: true, should_edit: false

Special cases:
- "save it/that/this" → Save content from conversation history to a document
  * Check conversation history for content to save
  * If user mentioned a document name, use that document
  * If no document mentioned, check if content topic matches any existing document
  * If no match or misaligned → CREATE a new one with inferred name
  * If no document exists, CREATE a new one with inferred name

Document Resolution:
1. Name match: User says "update X" → find doc named X (case-insensitive)
2. **Content alignment check**: Verify request topic matches document topic
   * If misaligned and user didn't explicitly name document → CREATE_DOCUMENT instead
3. Content match: "add hotels" → find travel/itinerary doc (verify alignment)
4. Topic match: "edit the document about [topic]" → find doc with topic in name or content
   * Example: "edit the document about the latest Python features" → find doc with "latest Python features" or "Python" in name/content
5. Context: "save it", "add it there" → check conversation history for:
   - Content to save (from previous agent response)
   - Document reference (mentioned earlier)
   - Most recent document if no specific reference
   - **Validate alignment**: If content topic doesn't match document topic → CREATE_DOCUMENT
6. If multiple match → use most relevant (check alignment)
7. If no match found but user explicitly said "edit the document about [topic]" or "edit the document called [name]" → 
   * Set should_edit: true, document_id: null (will be handled gracefully)
   * intent_statement should indicate which document was intended
8. **If request topic doesn't align with any existing document topic** → should_create: true, should_edit: false

Edit Scope:
- "selective": Small changes (heading, section, add to X, save content, improve, update, enhance, make better) → preserve all else
  * "improve", "update", "enhance", "make better", "refine" → ALWAYS selective
  * Preserve ALL sections and content, only modify what's requested
- "full": Large changes (rewrite entire, restructure, complete overhaul) → preserve structure
  * Only use "full" if user explicitly says "rewrite entire" or "complete overhaul"
  * Even for "full", preserve ALL sections and headings

CRITICAL: For selective edits, preserve ALL other content unchanged. For "full" edits, preserve ALL sections even if content is rewritten.
CRITICAL: Always validate content alignment before editing. If misaligned and user didn't explicitly name document → CREATE_DOCUMENT instead.
""")
        
        elif intent_type == "create":
            sections.append("""
=== CREATE REQUEST ===
BEFORE creating:
1. Infer doc name from request:
   - "create a script" → "Script" or "Video Script"
   - "create a [noun]" → capitalize the noun (e.g., "create a plan" → "Plan")
   - "make a new [noun]" or "make a new document" → capitalize the noun or use "New Document"
   - "make a new document about [topic]" → use topic as name (e.g., "Python" or "Python Guide")
2. Check if doc with that name exists → if yes, EDIT instead (UNLESS user explicitly said "new document" - then create with different name)
3. Only create if NO matching name exists OR user explicitly said "new document"

CRITICAL: "make a new document" or "make a new [thing]" keywords take PRIORITY:
- If user says "make a new document about Python" → should_create: true (even if "Python" document exists)
- Create a NEW document, don't edit existing one
- If name conflict, append number or use topic as name

Document Name:
- Extract from user message intelligently
- Patterns: "create a script" → "Script", "create a plan" → "Plan", "create a video script" → "Video Script"
- "make a new document about [topic]" → use topic as name
- Capitalize properly ("recipes" → "Recipes", "script" → "Script")
- REQUIRED if should_create is true

Document Content:
- If user asks to "create a script" or similar, generate the content based on:
  * Context from conversation history
  * References to other documents mentioned
  * The purpose inferred from the request
- Include the actual content in document_content field
""")
        
        elif intent_type == "clarify":
            sections.append("""
=== CLARIFICATION NEEDED ===
Only ask when:
- Multiple docs could match AND truly ambiguous
- Info doesn't exist AND can't be inferred
- Intent completely unclear

FORBIDDEN: Don't ask if info exists in docs or can be inferred.
""")
        
        else:
            # Default: include all sections (fallback)
            sections.append("""
=== INTENT CLASSIFICATION ===
1. CONVERSATION: Questions, greetings (should_edit: false)
2. EDIT: Modify existing (action words + doc reference)
3. CREATE: New doc (check name first!)
4. CLARIFY: Missing info (only when truly needed)

=== DOCUMENT RESOLUTION ===
- Check names first (case-insensitive match)
- Then content match
- Then context inference
- Create only if NO match found
""")
        
        # Common sections (always include)
        # Calculate most recent December for examples
        most_recent_december_year = current_year - 1 if current_month < 12 else current_year
        
        common = f"""
=== WEB SEARCH ===
ALWAYS search for:
- General knowledge questions (not about documents): "who is", "what is", "when did", "where is" (current information)
  Examples: "who is the current president", "what is the capital of France", "when did X happen"
  These are pure information-seeking questions that need current/accurate answers
- Questions about recent events/changes: "latest changes", "recent events", "what happened in [month/year]", "latest [thing] changes"
  Examples: "what are the latest US administration changes", "recent policy changes", "what happened in December" (use most recent December: December {most_recent_december_year})
  These questions ask about current/recent events that need up-to-date information
- "latest", "current", "new version", "recent", "up-to-date" (version numbers, release dates)
- "latest [thing]" (e.g., "latest Python version", "latest React features")
- "current [thing]" (e.g., "current prices", "current best practices")
- Safety-critical information, new products, current prices, time-sensitive data
- Travel/location information, real-time data

CRITICAL: If editing a document that is ABOUT "latest [thing]" or "current [thing]" (check document name/content):
- Even if user says "make more verbose", "expand", "improve", "update" → needs_web_search: true
- Reason: Documents about "latest" topics need current information to ensure accuracy
- Example: "edit the document about latest Python features" → needs_web_search: true, search_query: "latest Python features {current_year}"

Examples requiring web search:
- "add the latest Python version" → needs_web_search: true, search_query: "latest Python version {current_year}"
- "update with current React best practices" → needs_web_search: true, search_query: "React best practices {current_year}"
- "edit the document about latest Python features" → needs_web_search: true, search_query: "latest Python features {current_year}"
- "make the latest features doc more verbose" → needs_web_search: true, search_query: "latest Python features {current_year}"
- "add current Bitcoin price" → needs_web_search: true, search_query: "Bitcoin price today"
- "what's the latest version" → needs_web_search: true (conversation intent)
- "what happened in December" → needs_web_search: true, search_query: "US administration changes December {most_recent_december_year}" (use most recent December based on current date: {current_date_str})

CRITICAL - Search Query Generation:
- When generating search_query, ALWAYS use the current year ({current_year}) unless the user explicitly mentions a different year
- For month-only queries (e.g., "what happened in December"), infer the most recent occurrence based on current date ({current_date_str})
- Example: If user asks "what happened in December" and today is January {current_year}, search for "December {current_year - 1}"
- Example: If user asks "what happened in December" and today is December {current_year}, search for "December {current_year}"
- Example: If user asks "what happened in January" and today is March {current_year}, search for "January {current_year}" (most recent)

Never search: Stable knowledge (e.g., "how to write a function"), creative content, user's personal notes

=== DESTRUCTIVE ACTIONS ===
Set pending_confirmation: true for delete, remove, clear, large structural changes

=== RESPONSE FORMAT ===
JSON response:
{{
    "should_edit": boolean,
    "should_create": boolean,
    "document_id": integer|null,
    "document_name": string|null,  // Required if should_create
    "document_content": string|null,
    "standing_instruction": string|null,
    "edit_scope": "selective"|"full"|null,
    "needs_clarification": boolean,
    "pending_confirmation": boolean,
    "needs_web_search": boolean,
    "search_query": string|null,
    "clarification_question": string|null,
    "confirmation_prompt": string|null,
    "intent_statement": string|null,
    "reasoning": string,
    "conversational_response": string|null,
    "change_summary": string|null,
    "content_summary": string|null  // 3-5 sentences, 100-200 words
}}

Field Rules:
- should_edit: true for explicit edit requests including "save it/that/this"
  * "save it" → should_edit: true, get content from conversation history
  * "Edit [document] and add/update/change [X]" → should_edit: true (ALWAYS, document name is mentioned)
  * "Add [X] to [document]" → should_edit: true (ALWAYS, document name is mentioned)
  * If no document_id found but content exists → create new document instead
- should_create: true for "create a [noun]" patterns (e.g., "create a script")
  * MUST check if document with that name exists first
  * If exists → should_edit: true instead
  * CRITICAL: "Edit [document] and add [X]" is NOT create, it's edit
- document_id: Required if should_edit, resolve by:
  * Name match (user mentioned document name, e.g., "Edit the Python guide" → find "Python guide")
  * Context from conversation history
  * Most recent/relevant document if ambiguous
  * If truly unclear → needs_clarification: true
- needs_web_search: true if request contains:
  * "latest", "current", "new version", "recent", "up-to-date", version numbers, release dates
  * "latest [thing]", "current [thing]", "new [thing] version"
  * Time-sensitive information, current prices, real-time data
  * **General knowledge questions requiring current/real-time information: "who is", "what is", "when did", "where is" (for current info)**
    - CRITICAL: Questions like "who is the current president" ALWAYS need web search because the answer may have changed
    - Examples: "who is the current president", "what is the capital of France", "when did X happen" (if asking about recent events)
    - Pattern: If question asks about CURRENT/REAL-TIME information → needs_web_search: true
  * **OR if the document being edited is ABOUT "latest [thing]" or "current [thing]" (check document name/content)**
  * Examples: "latest Python version", "current React practices", "new features in {current_year}"
  * Example: "edit document about latest Python features" → needs_web_search: true (even if just "make verbose")
- search_query: Required if needs_web_search: true
  * Extract the searchable part and ALWAYS include the CURRENT YEAR ({current_year}) unless user explicitly mentions a different year
  * Examples: "latest Python version {current_year}", "current React best practices {current_year}"
  * For month-only queries: Use the most recent occurrence (e.g., if today is January {current_year} and user asks about "December", use "December {current_year - 1}")
  * CRITICAL: Always use {current_year} in search queries unless user explicitly mentions a different year
- document_content: 
  * For "create a script" → generate the script content here
  * For "save it" → extract content from conversation history (previous agent response)
- edit_scope: "selective" for small changes including "save it", "full" for large
- content_summary: Required if should_edit or should_create (describe what was/will be added)
  * Use first-person active voice WITHOUT pronouns ("I", "we", "the agent")
  * Start with action verbs: "Added...", "Updated...", "Created...", "Expanded...", "Included..."
  * DO NOT use third person: "The document now includes..." ❌
  * DO NOT use first person with pronouns: "I added..." or "We created..." ❌
  * CORRECT: "Added a section discussing backward compatibility with CUDA drivers..." ✅
  * CORRECT: "Created a new document with sections on..." ✅
"""
        
        # Examples (compressed - limit to 2000 chars)
        examples = ""
        if PROMPT_EXAMPLES:
            examples = f"\n=== EXAMPLES ===\n{PROMPT_EXAMPLES[:2000]}"
        
        prompt = core + "".join(sections) + common + examples
        
        return prompt
    
    @staticmethod
    def get_document_rewrite_prompt(
        user_message: str,
        standing_instruction: str,
        current_content: str,
        web_search_results: Optional[str] = None,
        edit_scope: Optional[str] = None,
        validation_errors: Optional[List[str]] = None
    ) -> str:
        """Compressed rewrite prompt"""
        scope_instructions = {
            "selective": f"""SELECTIVE EDIT - Build upon existing content:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

1. **Read the Current Content first**: Understand the structure, format, style, and existing information
2. **Understand the context**: What sections exist? What's the current format? What information is already there?
3. **Identify what needs to change**: Based on "{user_message}", determine what specific parts need updating
4. **Build upon existing content**: 
   - Keep the same structure, format, and style
   - Update only the relevant parts while preserving everything else
   - If user provides new context (e.g., "my skin is oily"), tailor the existing content to incorporate this context
   - Match the existing tone, formatting, and organization
5. **Preserve ALL other content exactly**: Everything not mentioned in the request stays the same

Examples:
- "replace heading" → change ONLY heading text, keep everything else
- "add to section X" → modify ONLY section X, preserve rest
- "my skin is oily" → update product recommendations in existing routine to suit oily skin, keep same structure
- "change title" → change ONLY title, preserve all content""",
            
            "full": """FULL REWRITE - Preserve ALL sections and structure:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

- You may modify content extensively BUT must preserve:
  * ALL headings and sections (even if you rewrite their content)
  * Document structure and organization
  * All major sections mentioned in original
- DO NOT remove sections unless explicitly asked
- If improving/updating: enhance content but keep all sections
- If restructuring: maintain all original sections, just reorganize
- CRITICAL: Every heading in original must appear in output
- Build upon the existing content, don't replace it entirely unless explicitly asked""",
            
            None: f"""Preserve ALL content unless explicitly asked to remove:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

1. **Read the Current Content first**: Understand what's already there
2. **Understand the context**: Structure, format, existing information
3. **Identify what to change**: Based on "{user_message}", determine what needs updating
4. **Build upon existing content**: Update relevant parts while preserving structure and style
5. **Preserve everything else**: All content not mentioned in the request stays the same"""
        }
        
        scope_text = scope_instructions.get(edit_scope, scope_instructions[None])
        
        # Build web search section separately to avoid f-string backslash issue
        web_search_section = ""
        web_search_instructions = ""
        if web_search_results:
            web_search_section = f"\nWeb Search Results:\n{web_search_results}\n"
            # Extract URLs from web search results for validation
            import re
            url_pattern = r'URL:\s*(https?://[^\s\n]+)'
            urls_found = re.findall(url_pattern, web_search_results)
            title_pattern = r'Title:\s*([^\n]+)'
            titles_found = re.findall(title_pattern, web_search_results)
            
            # Build sources list for reference
            sources_list = []
            for i, url in enumerate(urls_found):
                title = titles_found[i] if i < len(titles_found) else "Source"
                sources_list.append(f"- [{title}]({url})")
            
            web_search_instructions = f"""
================================================================================
MANDATORY - Web Search Source Attribution (CRITICAL - DO NOT SKIP):
================================================================================
Web search results have been provided above. You MUST include source attribution.

The web search results are formatted as:
Title: [Title]
URL: [URL]
Content: [Content]
---

REQUIRED STEPS (YOU MUST DO THIS):
1. Find ALL "URL:" lines in the web search results above
2. Extract the Title from the line immediately before each URL
3. Add a "## Sources" section at the VERY END of the document (after all other content)
4. Format each source as: - [Title](URL)
5. Include ALL URLs from the web search results, even if you only used part of the content

Expected Sources Section Format:
## Sources
{sources_list[0] if sources_list else "- [Source Title](URL)"}
{sources_list[1] if len(sources_list) > 1 else ""}
{sources_list[2] if len(sources_list) > 2 else ""}
{sources_list[3] if len(sources_list) > 3 else ""}
{sources_list[4] if len(sources_list) > 4 else ""}

CRITICAL RULES:
- The document output MUST end with a "## Sources" section
- The Sources section MUST be the last thing in the document
- You MUST include ALL URLs from the web search results
- DO NOT skip this step - it is mandatory
- If you skip this, the document is incomplete and invalid

VALIDATION: Before returning your response, check that your document ends with:
## Sources
- [Title](URL)
- [Title](URL)
...

If it doesn't, add it now.
================================================================================
"""
        
        # Build validation errors section if present
        validation_section = ""
        if validation_errors:
            validation_section = f"""

CRITICAL - Previous attempt had validation issues:
{chr(10).join(validation_errors)}

You MUST fix these issues:
- Restore ALL missing sections mentioned above
- Preserve ALL original headings and sections
- Only modify what was requested, keep everything else intact"""
        
        prompt = f"""Update document based on user request. Request: "{user_message}"

CRITICAL: Read the "Current Content" section below FIRST before making any changes.
Understand the existing structure, format, and content, then build upon it.

Standing Instruction: {standing_instruction}

=== CURRENT CONTENT (READ THIS FIRST) ===
{current_content}
=== END OF CURRENT CONTENT ===

{scope_text}
{web_search_section}{web_search_instructions}{validation_section}

IMPORTANT - Track Your Changes:
- As you make changes, be aware of what you're modifying:
  * Which sections did you update?
  * What specific information did you add, remove, or change?
  * Did you tailor existing content to new context (e.g., updated product recommendations for specific skin type)?
- This awareness will help ensure changes are accurate and complete
- Keep track mentally of: what was there → what changed → what's now there

Output Requirements:
- Pure markdown (NO HTML tags)
- Preserve ALL formatting: tables, links, images, code blocks, lists, headings
- Preserve ALL sections not mentioned in request
- Build upon existing content - don't replace it unless explicitly asked
- Match existing style, tone, and format
- **MANDATORY: If web search results were provided above, the document MUST end with a "## Sources" section**
- **The Sources section must list ALL URLs from the web search results in format: - [Title](URL)**
- Return ONLY markdown content (no explanations)
- Be aware of what you changed so you can accurately describe modifications if needed"""
        
        return prompt
    
    @staticmethod
    def get_conversational_prompt(
        user_message: str,
        context: str = "",
        web_search_results: Optional[str] = None
    ) -> str:
        """Compressed conversational prompt"""
        user_lower = user_message.lower()
        
        # Get current date information dynamically
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        current_date_str = now.strftime('%B %d, %Y')
        
        # Calculate most recent December for example
        if current_month == 12:
            most_recent_december = f"December {current_year}"
        else:
            most_recent_december = f"December {current_year - 1}"
        
        # Build web search section separately to avoid f-string backslash issue
        web_search_section = ""
        if web_search_results:
            web_search_section = f"""

Web Search Results (use this information to answer the user's question):
{web_search_results}
"""
        
        # Special handling for location questions
        if any(keyword in user_lower for keyword in ["where", "where did", "where is", "what did you"]):
            return f"""User is asking about location/status of documents or changes.

Context from conversation history:
{context}
{web_search_section}
User question: "{user_message}"

Provide a clear answer:
- If context mentions a document was created/updated, tell user the document name
- Reference specific document names from the context
- Be specific about what was done and where
- If you see "Recent document operations" in context, use that information
- If web search results are provided, use them to provide accurate, up-to-date information

Answer: Provide the information directly. If including a closing statement (e.g., "If you have any more questions..."), add 2-3 blank lines BEFORE the closing statement to visually separate the answer from the pleasantry."""
        else:
            # Build the prompt with web search results prominently displayed
            prompt_parts = []
            
            # Start with web search results if available (most important)
            if web_search_results:
                prompt_parts.append(f"""=== WEB SEARCH COMPLETED ===
A web search has ALREADY been performed. The results are below.

SEARCH RESULTS:
{web_search_results}

=== YOUR TASK ===
Read the search results above and answer this question: "{user_message}"

MANDATORY FORMAT:
- Start your response IMMEDIATELY with the answer
- Extract the answer from the "Content:" sections in the search results above
- For "who is" questions, use the EXACT name from the Content sections
- The search results are MORE CURRENT than your training data (current as of {current_date_str})

DO NOT:
- Say "I will search" (search is already done)
- Say "Let me look" (results are above)
- Use future tense like "I'll search"

DO:
- Extract the answer from the "Content:" sections above
- Start immediately with the answer
- Use the exact information from the results

Answer now:""")
            else:
                prompt_parts.append(f"""Helpful assistant for document management.

CURRENT USER QUESTION (answer this one): "{user_message}"

CRITICAL: Answer the question above. Chat history below is for context only - do not answer previous questions.
""")
            
            # Add context if available
            if context:
                prompt_parts.append(f"Context: {context}\n")
            
            # Add remaining instructions
            if web_search_results:
                # If web search results are provided, skip redundant instructions (already covered above)
                prompt_parts.append(f"""Response: Helpful, friendly, concise. Answer the user's question directly using the web search results provided above.

CRITICAL - Response Format:
- Start IMMEDIATELY with the answer from web search results
- Example: "The current president of the United States is [Name from web search results]..."
- DO NOT say "I will search" or "Let me look that up" - the search is already done
- DO NOT use future tense like "I'll search" - use present tense with the information from results

Current date context: Today is {current_date_str}, current year is {current_year}
- When user asks about "this year" or "current year" → use {current_year}
- When user asks about a month without a year (e.g., "December", "January", "March") → use the most recent occurrence of that month based on current date
  * Example: If current date is January {current_year} and user asks "what happened in December" → December {current_year - 1} (most recent)
  * Example: If current date is March {current_year} and user asks "what happened in January" → January {current_year} (most recent)
  * Example: If current date is March {current_year} and user asks "what happened in December" → December {current_year - 1} (most recent)
  * Always infer the most recent occurrence based on the current date ({current_date_str})

CRITICAL - Formatting for closing statements:
- If you include a closing pleasantry (e.g., "If you have any more questions...", "Feel free to ask!", etc.)
- Add 2-3 blank lines (line breaks) BEFORE the closing statement
- This visually separates the actual information from the closing pleasantry
- Example format:
  [Actual answer/information]
  
  
  If you have any more questions or need assistance with something else, feel free to ask!
""")
            else:
                # No web search results - include general instructions
                prompt_parts.append(f"""Context: Use conversation history for follow-ups ("yeah", "yes", "do it" refer to previous messages).

Response: Helpful, friendly, concise. For "summarize" or "read", provide content summary in chat.

Current date context: Today is {current_date_str}, current year is {current_year}
- When user asks about "this year" or "current year" → use {current_year}
- When user asks about a month without a year (e.g., "December", "January", "March") → use the most recent occurrence of that month based on current date
  * Example: If current date is January {current_year} and user asks "what happened in December" → December {current_year - 1} (most recent)
  * Example: If current date is March {current_year} and user asks "what happened in January" → January {current_year} (most recent)
  * Example: If current date is March {current_year} and user asks "what happened in December" → December {current_year - 1} (most recent)
  * Always infer the most recent occurrence based on the current date ({current_date_str})

CRITICAL - Formatting for closing statements:
- If you include a closing pleasantry (e.g., "If you have any more questions...", "Feel free to ask!", etc.)
- Add 2-3 blank lines (line breaks) BEFORE the closing statement
- This visually separates the actual information from the closing pleasantry
- Example format:
  [Actual answer/information]
  
  
  If you have any more questions or need assistance with something else, feel free to ask!
""")
            
            return "".join(prompt_parts)
