"""
Agent Decision Template

Template for agent decision prompts (Stage 2 of two-stage prompting).
Handles conversation, edit, create, and clarify intent types.
"""

from typing import Dict, Any, Optional
from .base import PromptTemplate
from ..utils import (
    get_current_date_context,
    build_documents_list
)


class AgentDecisionTemplate(PromptTemplate):
    """Template for agent decision prompts."""
    name = "agent_decision"
    version = "v1"
    
    def __init__(self, intent_type: str):
        """
        Initialize template.
        
        Args:
            intent_type: "conversation", "edit", "create", "delete", or "clarify"
        """
        self.intent_type = intent_type
    
    def render(self, policy_text: str, runtime: Dict[str, Any]) -> str:
        """Render agent decision prompt."""
        user_message = runtime["user_message"]
        documents = runtime.get("documents", [])
        project_context = runtime.get("project_context")
        intent_metadata = runtime.get("intent_metadata")
        
        # Get current date
        date_ctx = get_current_date_context()
        current_year = date_ctx["current_year"]
        current_month = date_ctx["current_month"]
        current_date_str = date_ctx["current_date_str"]
        most_recent_december_year = date_ctx["most_recent_december_year"]
        
        # Build document list
        documents_list = build_documents_list(documents)
        
        # Build project info
        project_info = ""
        if project_context:
            project_info = f"Project: {project_context.get('name', 'Unknown')} (id:{project_context.get('id')})"
        
        # Build intent context
        intent_context = self._build_intent_context(intent_metadata)
        
        # Build task with context
        task_parts = []
        if project_info:
            task_parts.append(project_info)
        if intent_context:
            task_parts.append(intent_context)
        task_parts.append(f"Current Date Context: Today is {current_date_str}, current year is {current_year}")
        task_parts.append("")
        task_parts.append("Documents:")
        task_parts.append(documents_list)
        task_parts.append("")
        task_parts.append(f'User: "{user_message}"')
        
        task = "\n".join(task_parts)
        
        # Add intent-specific sections to task
        if self.intent_type == "conversation":
            task += "\n\n" + self._render_conversation_task_section(current_year, current_month, current_date_str)
        elif self.intent_type == "edit":
            task += "\n\n" + self._render_edit_task_section()
        elif self.intent_type == "create":
            task += "\n\n" + self._render_create_task_section()
        elif self.intent_type == "delete":
            task += "\n\n" + self._render_delete_task_section()
        elif self.intent_type == "clarify":
            task += "\n\n" + self._render_clarify_task_section()
        
        # Add common sections (web search, destructive actions)
        task += "\n\n" + self._render_common_task_sections(current_year, current_month, current_date_str, most_recent_december_year)
        
        # Build output format
        output_format = """{
    "should_edit": boolean,
    "should_create": boolean,
    "should_delete": boolean,
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
}"""
        
        # Get examples if available
        examples = ""
        try:
            from ...prompts.examples import PROMPT_EXAMPLES
            if PROMPT_EXAMPLES:
                examples = f"\n\nEXAMPLES (do not override rules):\n{PROMPT_EXAMPLES[:2000]}"
        except ImportError:
            pass
        
        return f"""{policy_text}

TASK:
{task}

OUTPUT FORMAT:
{output_format}{examples}"""
    
    def _build_intent_context(self, intent_metadata: Optional[Dict]) -> str:
        """Build intent context from metadata."""
        if not intent_metadata:
            return ""
        
        action = intent_metadata.get("action")
        targets = intent_metadata.get("targets", [])
        intent_statement = intent_metadata.get("intent_statement", "")
        
        intent_context = f"STAGE 1 CLASSIFICATION:\n- Action: {action}\n- Intent: {intent_statement}\n- Target Documents: {len(targets)} document(s) identified"
        
        if targets:
            primary_target = next((t for t in targets if t.get("role") == "primary"), None)
            if primary_target:
                intent_context += f"\n- Primary target: {primary_target.get('document_name')} (id: {primary_target.get('document_id')})"
                if primary_target.get('summary'):
                    intent_context += f"\n  Summary: {primary_target.get('summary')}"
        
        return intent_context
    
    def _render_conversation_task_section(self, current_year: int, current_month: int, current_date_str: str) -> str:
        """Render conversation-specific task section."""
        most_recent_dec = current_year - 1 if current_month < 12 else current_year
        return f"""**CRITICAL: This is a CONVERSATION/ANSWER_ONLY action from Stage 1**
- should_edit: MUST be false (do NOT edit documents)
- should_create: MUST be false (do NOT create documents)
- This is a conversational response, not a document operation
- Only provide answers, explanations, or information

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
- For location questions: Reference specific document names and what was done"""
    
    def _render_edit_task_section(self) -> str:
        """Render edit-specific task section."""
        return """Action words: add, update, change, remove, edit, rewrite, modify, delete, insert, save, put

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
CRITICAL: Always validate content alignment before editing. If misaligned and user didn't explicitly name document → CREATE_DOCUMENT instead."""
    
    def _render_create_task_section(self) -> str:
        """Render create-specific task section."""
        return """BEFORE creating:
1. Infer doc name from request:
   - "create a script" → "Script" or "Video Script"
   - "create a [noun]" → capitalize the noun (e.g., "create a plan" → "Plan")
   - "make a new [noun]" or "make a new document" → capitalize the noun or use "New Document"
   - "make a new document about [topic]" → use topic as name (e.g., "Python" or "Python Guide")
   - **CRITICAL: "write/create/make a document on it/that/this" → extract topic from MOST RECENT assistant response**
     * Check the last assistant message in conversation history (most recent response)
     * Extract the main topic/subject from that response
     * Use that topic for document name
     * Example: Last response was "Trump's policies include..." → document_name: "Trump Policies" or "Trump's Policies"
     * Example: Last response was about "US immigration" → document_name: "US Immigration" (if not exists) or "US Immigration Policies"
     * Priority: Most recent assistant response > Earlier conversation > General topic
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
- **"write/create/make a document on it/that/this" → extract from most recent assistant response**
- Capitalize properly ("recipes" → "Recipes", "script" → "Script")
- REQUIRED if should_create is true

Document Content:
- If user asks to "create a script" or similar, generate the content based on:
  * Context from conversation history
  * References to other documents mentioned
  * The purpose inferred from the request
- Include the actual content in document_content field"""
    
    def _render_delete_task_section(self) -> str:
        """Render delete-specific task section."""
        return """BEFORE deleting:
1. Document Resolution:
   - Name match: User says "delete X" → find doc named X (case-insensitive)
   - Context: "delete it", "remove it" → check conversation history for most recent document reference
   - Anaphoric reference: "the document", "it", "that document" → resolve from conversation history
   - Resolution priority: Most recent document reference > Document mentioned in previous assistant response > Most recently created/updated document
   - If multiple match → use most relevant
   - If no match found → needs_clarification: true

2. Confirmation Handling:
   - CRITICAL: Always set pending_confirmation: true for deletion requests (destructive action)
   - When user says "yes", "ok", "go ahead", "proceed", "sure" after confirmation prompt:
     * Check chat history for the most recent message with pending_confirmation: true
     * If found with should_delete: true → set should_delete: true, pending_confirmation: false
     * Execute the deletion
   - When user says "no", "cancel", "don't" → set should_delete: false, pending_confirmation: false

3. Deletion Rules:
   - should_delete: true only when:
     * User explicitly requests deletion ("delete [document]", "remove [document]", "delete it", "remove it")
     * User confirms deletion after confirmation prompt ("yes" after "Are you sure...")
   - document_id: Required if should_delete: true
   - intent_statement: Required if should_delete (describe completed action in first person past tense)
     * Format: "I have deleted [document name]."
     * Example: "I have deleted the document about Policies Under Secretary of Defense Pete Hegseth."
   - confirmation_prompt: Required if pending_confirmation: true
     * Format: "Are you sure you want to delete [document name]?"
     * Include document name for clarity

4. CRITICAL: Deletion is permanent and cannot be undone
   - Always request confirmation before deleting
   - Only proceed when user explicitly confirms
   - Do NOT delete if user says "no" or "cancel"
"""
    
    def _render_clarify_task_section(self) -> str:
        """Render clarify-specific task section."""
        return """Only ask when:
- Multiple docs could match AND truly ambiguous
- Info doesn't exist AND can't be inferred
- Intent completely unclear

FORBIDDEN: Don't ask if info exists in docs or can be inferred."""
    
    def _render_common_task_sections(
        self,
        current_year: int,
        current_month: int,
        current_date_str: str,
        most_recent_december_year: int
    ) -> str:
        """Render common task sections for all intent types."""
        return f"""WEB SEARCH:
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

DESTRUCTIVE ACTIONS:
Set pending_confirmation: true for delete, remove, clear, large structural changes

CONFIRMATION HANDLING:
- When user says "yes", "ok", "go ahead", "proceed", "sure" after a confirmation prompt:
  * Check chat history for the most recent message with pending_confirmation: true
  * If found, inherit the action (should_edit, should_create, should_delete) from that pending confirmation
  * Execute the action that was pending confirmation
  * Example: Previous message had pending_confirmation: true, should_delete: true → set should_delete: true, pending_confirmation: false
  * Example: Previous message had pending_confirmation: true, should_edit: true → set should_edit: true, pending_confirmation: false
- When user says "no", "cancel", "don't" → set should_edit: false, should_create: false, should_delete: false, pending_confirmation: false

FIELD RULES:
- should_edit: true for explicit edit requests including "save it/that/this"
  * "save it" → should_edit: true, get content from conversation history
  * "Edit [document] and add/update/change [X]" → should_edit: true (ALWAYS, document name is mentioned)
  * "Add [X] to [document]" → should_edit: true (ALWAYS, document name is mentioned)
  * If no document_id found but content exists → create new document instead
- should_create: true for "create a [noun]" patterns (e.g., "create a script")
  * MUST check if document with that name exists first
  * If exists → should_edit: true instead
  * CRITICAL: "Edit [document] and add [X]" is NOT create, it's edit
- should_delete: true for explicit delete/remove requests
  * "delete [document]", "remove [document]", "delete it", "remove it" → should_delete: true
  * "yes" after confirmation prompt about deletion → should_delete: true (check chat history for pending_confirmation)
  * CRITICAL: Set pending_confirmation: true for deletion requests (destructive action)
  * Only set should_delete: true when user explicitly confirms (e.g., "yes", "go ahead", "delete it")
- document_id: Required if should_edit or should_delete, resolve by:
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
- intent_statement: Required if should_edit, should_create, or should_delete (describe completed action in first person past tense)
  * Format: "I have [verb]..." (e.g., "I have rewritten...", "I have updated...", "I have fixed...")
  * DO NOT use third person: "User wants to..." ❌
  * DO NOT use future tense: "I will..." or "I'll..." ❌
  * CORRECT: "I have rewritten the document to fix the dummy source section" ✅
  * CORRECT: "I have updated the document to add the latest Python features" ✅
  * CORRECT: "I have deleted the document about Policies Under Secretary of Defense Pete Hegseth" ✅
- content_summary: Required if should_edit or should_create (describe what was/will be added)
  * Use first-person active voice WITHOUT pronouns ("I", "we", "the agent")
  * Start with action verbs: "Added...", "Updated...", "Created...", "Expanded...", "Included..."
  * DO NOT use third person: "The document now includes..." ❌
  * DO NOT use first person with pronouns: "I added..." or "We created..." ❌
  * CORRECT: "Added a section discussing backward compatibility with CUDA drivers..." ✅
  * CORRECT: "Created a new document with sections on..." ✅"""
