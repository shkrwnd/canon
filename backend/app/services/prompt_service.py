from typing import Dict, Any, Optional, List
import logging

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
    def classify_intent(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Stage 1: Fast intent classification prompt
        Returns prompt for classifying user intent with conversation context
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
  CRITICAL: "Add [X] to [document]" = edit (e.g., "Add hotels to the itinerary")
  NOT questions: "where did you save" = conversation (question), not edit
  CONFIRMATION: If recent conversation shows agent asked for confirmation (e.g., "Should I proceed?", "Shall I make the changes?") and user says "yes"/"ok"/"proceed"/"go ahead"/"sure" → edit
  
- "create": Create new doc (words: create, make, new document, script, outline, plan)
  Examples: "create a script", "create a [thing]", "make a new [thing]", "write a script"
  CRITICAL: "create a script" or "create a [noun]" = create (new document)
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
- "save it/that/this" → edit (save content to document)
- "add/update/change [content]" → edit (if document context exists)
- "Edit [document] and add/update/change [X]" → edit (ALWAYS, document name is mentioned)
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
    def get_agent_decision_prompt(
        user_message: str,
        documents: list,
        project_context: Optional[Dict] = None,
        intent_type: Optional[str] = None
    ) -> str:
        """
        Stage 2: Generate detailed decision prompt with dynamic sections
        Only includes relevant sections based on intent_type
        """
        documents_list = PromptService._build_compressed_documents_list(documents)
        
        project_info = ""
        if project_context:
            project_info = f"Project: {project_context.get('name', 'Unknown')} (id:{project_context.get('id')})\n"
        
        # Core rules (always included)
        core = f"""You're a document maintainer. Keep docs accurate and structured.
{project_info}

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
            sections.append("""
=== CONVERSATION RESPONSE ===
Provide helpful response:
- General knowledge questions (not about documents): Use web search if needed, provide direct answer
  * "who is the current president" → needs_web_search: true, search_query: "current president of US"
  * "what is the capital of France" → needs_web_search: true, search_query: "capital of France"
  * Answer directly based on web search results or your knowledge
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

Special cases:
- "save it/that/this" → Save content from conversation history to a document
  * Check conversation history for content to save
  * If user mentioned a document name, use that document
  * If no document mentioned, infer from context or use most recent/relevant document
  * If no document exists, CREATE a new one with inferred name

Document Resolution:
1. Name match: User says "update X" → find doc named X (case-insensitive)
2. Content match: "add hotels" → find travel/itinerary doc
3. Context: "save it", "add it there" → check conversation history for:
   - Content to save (from previous agent response)
   - Document reference (mentioned earlier)
   - Most recent document if no specific reference
4. If multiple match → use most relevant

Edit Scope:
- "selective": Small changes (heading, section, add to X, save content, improve, update, enhance, make better) → preserve all else
  * "improve", "update", "enhance", "make better", "refine" → ALWAYS selective
  * Preserve ALL sections and content, only modify what's requested
- "full": Large changes (rewrite entire, restructure, complete overhaul) → preserve structure
  * Only use "full" if user explicitly says "rewrite entire" or "complete overhaul"
  * Even for "full", preserve ALL sections and headings

CRITICAL: For selective edits, preserve ALL other content unchanged. For "full" edits, preserve ALL sections even if content is rewritten.
""")
        
        elif intent_type == "create":
            sections.append("""
=== CREATE REQUEST ===
BEFORE creating:
1. Infer doc name from request:
   - "create a script" → "Script" or "Video Script"
   - "create a [noun]" → capitalize the noun (e.g., "create a plan" → "Plan")
   - "make a [noun]" → same as above
2. Check if doc with that name exists → if yes, EDIT instead
3. Only create if NO matching name exists

Document Name:
- Extract from user message intelligently
- Patterns: "create a script" → "Script", "create a plan" → "Plan", "create a video script" → "Video Script"
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
        common = """
=== WEB SEARCH ===
ALWAYS search for:
- General knowledge questions (not about documents): "who is", "what is", "when did", "where is" (current information)
  Examples: "who is the current president", "what is the capital of France", "when did X happen"
  These are pure information-seeking questions that need current/accurate answers
- "latest", "current", "new version", "recent", "up-to-date", "2024", "2025" (version numbers, release dates)
- "latest [thing]" (e.g., "latest Python version", "latest React features")
- "current [thing]" (e.g., "current prices", "current best practices")
- Safety-critical information, new products, current prices, time-sensitive data
- Travel/location information, real-time data

CRITICAL: If editing a document that is ABOUT "latest [thing]" or "current [thing]" (check document name/content):
- Even if user says "make more verbose", "expand", "improve", "update" → needs_web_search: true
- Reason: Documents about "latest" topics need current information to ensure accuracy
- Example: "edit the document about latest Python features" → needs_web_search: true, search_query: "latest Python features 2024"

Examples requiring web search:
- "add the latest Python version" → needs_web_search: true, search_query: "latest Python version 2024"
- "update with current React best practices" → needs_web_search: true, search_query: "React best practices 2024"
- "edit the document about latest Python features" → needs_web_search: true, search_query: "latest Python features 2024"
- "make the latest features doc more verbose" → needs_web_search: true, search_query: "latest Python features 2024"
- "add current Bitcoin price" → needs_web_search: true, search_query: "Bitcoin price today"
- "what's the latest version" → needs_web_search: true (conversation intent)

Never search: Stable knowledge (e.g., "how to write a function"), creative content, user's personal notes

=== DESTRUCTIVE ACTIONS ===
Set pending_confirmation: true for delete, remove, clear, large structural changes

=== RESPONSE FORMAT ===
JSON response:
{
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
}

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
  * **OR if the document being edited is ABOUT "latest [thing]" or "current [thing]" (check document name/content)**
  * Examples: "latest Python version", "current React practices", "new features in 2024"
  * Example: "edit document about latest Python features" → needs_web_search: true (even if just "make verbose")
- search_query: Required if needs_web_search: true
  * Extract the searchable part (e.g., "latest Python version 2024", "current React best practices")
  * Include version numbers or years if mentioned
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
            "selective": f"""SELECTIVE EDIT - Preserve everything else:
1. Parse structure (headings, sections, tables, links)
2. Identify what to change (based on: "{user_message}")
3. Preserve ALL other content exactly
4. Modify ONLY identified parts

Examples:
- "replace heading" → change ONLY heading text
- "add to section X" → modify ONLY section X
- "change title" → change ONLY title""",
            
            "full": """FULL REWRITE - Preserve ALL sections and structure:
- You may modify content extensively BUT must preserve:
  * ALL headings and sections (even if you rewrite their content)
  * Document structure and organization
  * All major sections mentioned in original
- DO NOT remove sections unless explicitly asked
- If improving/updating: enhance content but keep all sections
- If restructuring: maintain all original sections, just reorganize
- CRITICAL: Every heading in original must appear in output""",
            
            None: f"""Preserve ALL content unless explicitly asked to remove:
1. Parse structure
2. Identify what to change (based on: "{user_message}")
3. Preserve everything else"""
        }
        
        scope_text = scope_instructions.get(edit_scope, scope_instructions[None])
        
        # Build web search section separately to avoid f-string backslash issue
        web_search_section = ""
        web_search_instructions = ""
        if web_search_results:
            web_search_section = f"\nWeb Search Results:\n{web_search_results}\n"
            web_search_instructions = """
MANDATORY - Web Search Source Attribution:
The web search results above are formatted as:
Title: [Title]
URL: [URL]
Content: [Content]
---

YOU MUST:
1. Find ALL "URL:" lines in the web search results above
2. Extract the Title from the line immediately before each URL
3. Add a "## Sources" section at the VERY END of the document (after all other content)
4. Format each source as: - [Title](URL)
5. Include ALL URLs from the web search results, even if you only used part of the content

Example - If web search results contain:
Title: Python 3.13 Release Notes
URL: https://docs.python.org/3.13/whatsnew/
Content: ...

Then your document MUST end with:
## Sources
- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/)

CRITICAL: The document output MUST end with a "## Sources" section containing all URLs from the web search results.
If you skip this, the document is incomplete.
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
        
        prompt = f"""Rewrite document. Request: "{user_message}"

Standing Instruction: {standing_instruction}

Current Content:
{current_content}

{scope_text}
{web_search_section}{web_search_instructions}{validation_section}
Output Requirements:
- Pure markdown (NO HTML tags)
- Preserve ALL formatting: tables, links, images, code blocks, lists, headings
- Preserve ALL sections not mentioned in request
- **MANDATORY: If web search results were provided above, the document MUST end with a "## Sources" section**
- **The Sources section must list ALL URLs from the web search results in format: - [Title](URL)**
- Return ONLY markdown content (no explanations)"""
        
        return prompt
    
    @staticmethod
    def get_conversational_prompt(
        user_message: str,
        context: str = "",
        web_search_results: Optional[str] = None
    ) -> str:
        """Compressed conversational prompt"""
        user_lower = user_message.lower()
        
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
            return f"""Helpful assistant for document management.

User: "{user_message}"
{context}{web_search_section}

Context: Use conversation history for follow-ups ("yeah", "yes", "do it" refer to previous messages).
If web search results are provided, use them to answer questions with accurate, current information.

Response: Helpful, friendly, concise. For "summarize" or "read", provide content summary in chat.

CRITICAL - Formatting for closing statements:
- If you include a closing pleasantry (e.g., "If you have any more questions...", "Feel free to ask!", etc.)
- Add 2-3 blank lines (line breaks) BEFORE the closing statement
- This visually separates the actual information from the closing pleasantry
- Example format:
  [Actual answer/information]
  
  
  If you have any more questions or need assistance with something else, feel free to ask!"""
