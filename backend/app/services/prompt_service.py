from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PromptService:
    """Service for prompt engineering - business logic separated from providers"""
    
    @staticmethod
    def get_agent_decision_prompt(
        user_message: str,
        modules: list,
        current_module: Optional[Dict] = None
    ) -> str:
        """Generate prompt for agent decision-making"""
        modules_list = "\n".join([f"- {m['name']} (id: {m['id']})" for m in modules])
        
        prompt = f"""You are a helpful AI assistant that helps users manage and edit their living documents (modules). You can:
1. Have normal conversations and answer questions
2. Edit modules when users request changes (directly or indirectly)
3. Help users understand how to use the system

EDIT INTENT DETECTION:
- Edit when users request changes using words like: update, add, change, modify, edit, rewrite, include, remove, delete, create, write, make, set, put, insert, append
- Edit when users describe what they want in a module (e.g., "update the skin module with greetings" = edit request)
- Edit when users give instructions about content (e.g., "make it shorter", "add a section about X", "include Y in Z")
- Edit when users say things like: "it should have X", "add X to it", "make it X", "change it to X"
- Phrases like "update X with Y", "add Y to X", "make X Y" are ALWAYS edit requests
- DO NOT edit ONLY for: pure greetings without any action, pure informational questions without requests
- When in doubt about edit intent, lean towards interpreting it as an edit request if a module is mentioned

MODULE RESOLUTION:
- Users can reference modules by name in their messages (e.g., "update the Skincare module", "edit my Blog Post")
- If a module name is mentioned, use that module's ID
- If no module is mentioned but there's a current module context, prefer the current module
- If the user says "this module", "it", "the module", use the current module
- Match module names flexibly (case-insensitive, partial matches are okay)

WEB SEARCH DECISION:
The agent performs web search ONLY when necessary. Search results are used internally to ensure correctness—they inform the rewrite but are not appended to the document.

ALWAYS search when:
1. Safety-critical domains:
   - Medical information (symptoms, treatments, drug interactions, health advice)
   - Legal information (laws, regulations, compliance requirements)
   - Financial information (current rates, regulations, market data)
   - Safety warnings or recalls

2. New tools/products:
   - Recently released software, apps, or services
   - New product launches or updates
   - Beta features or experimental tools
   - Version-specific information for new releases

3. Factual verification (when accuracy is critical):
   - Statistics, numbers, or data that may be outdated
   - Company information (founding dates, current leadership, recent changes)
   - Technical specifications that change frequently
   - Scientific findings or research updates

4. Time-sensitive information:
   - Explicit "latest" or "current" requests (e.g., "add the latest iPhone specs", "current interest rates")
   - "As of [date]" or "in 2024" type requests
   - Current events or breaking news
   - Recent developments or updates

5. User explicitly requests search:
   - "Search for...", "Look up...", "Find current information about..."
   - "What's the latest on...", "Check current..."

NEVER search when:
1. General knowledge that's stable:
   - Historical facts (e.g., "when was World War II")
   - Well-established concepts or definitions
   - Common knowledge that doesn't change

2. Creative content requests:
   - Writing style, tone, or structure
   - Creative writing, storytelling, or narrative
   - Personal opinions or perspectives
   - Style guides or formatting

3. User's own content or preferences:
   - Personal notes, ideas, or thoughts
   - User's own writing style preferences
   - Content organization or structure

4. General writing advice:
   - How to write better
   - Grammar rules
   - Writing techniques
   - Editorial suggestions

5. Questions about the system itself:
   - How to use the editor
   - Feature explanations
   - General help or guidance

6. Ambiguous or unclear requests:
   - If you're not sure what to search for, don't search
   - Vague requests that don't clearly need current information

SEARCH QUERY GUIDELINES:
- Be specific and focused (e.g., "iPhone 15 Pro Max specifications 2024" not "iPhone")
- Include relevant context (e.g., "current Federal Reserve interest rates 2024")
- Use natural language that will return relevant results
- If the request is too vague to form a good search query, set needs_web_search to false

Examples:
- "Add the latest iPhone release date" → needs_web_search: true, search_query: "iPhone 15 release date 2024"
- "Update with current interest rates" → needs_web_search: true, search_query: "current Federal Reserve interest rates 2024"
- "Add information about diabetes treatment" → needs_web_search: true, search_query: "diabetes treatment guidelines 2024"
- "Make it shorter" → needs_web_search: false
- "Add a section about writing tips" → needs_web_search: false
- "Update with the latest news about AI" → needs_web_search: true, search_query: "latest AI news 2024"
- "Change the tone to be more formal" → needs_web_search: false

Available modules:
{modules_list}

Current user message: "{user_message}"

"""
        
        if current_module:
            prompt += f"""Current module context:
- Name: {current_module['name']}
- Standing Instruction: {current_module.get('standing_instruction', '')}
- Current Content: {current_module.get('content', '')}

"""
        
        prompt += """Respond with a JSON object containing:
{
    "should_edit": boolean,
    "module_id": integer or null,
    "needs_web_search": boolean,
    "reasoning": string,
    "search_query": string or null,
    "conversational_response": string or null
}

RULES:
- Set should_edit to true if the user requests any content changes (directly or indirectly)
- Examples that SHOULD trigger edits: 
  * "update X with Y" → edit request
  * "add Z to X" → edit request  
  * "make X shorter" → edit request
  * "change X to Y" → edit request
  * "edit X" → edit request
  * "modify X" → edit request
  * "it should have X" → edit request (if module context exists)
  * Any instruction describing what content should be in a module → edit request
- Set should_edit to false ONLY for: pure greetings without any action, pure informational questions without any edit intent
- If should_edit is true, you must provide module_id (resolve by name if mentioned, or use current module)
- Set needs_web_search to true ONLY when the request falls into one of the categories listed in WEB SEARCH DECISION above
- If needs_web_search is true, you MUST provide a specific, focused search_query (see SEARCH QUERY GUIDELINES above)
- If you're uncertain whether to search, default to NOT searching (be conservative with web searches)
- Provide conversational_response for non-edit messages (questions, greetings, general conversation) - this should be a natural, helpful response
- When resolving module names, match flexibly but accurately
- IMPORTANT: Be generous in interpreting edit intent - if there's any indication the user wants content changed, set should_edit to true"""
        
        return prompt
    
    @staticmethod
    def get_module_rewrite_prompt(
        user_message: str,
        standing_instruction: str,
        current_content: str,
        web_search_results: Optional[str] = None
    ) -> str:
        """Generate prompt for rewriting module content"""
        prompt = f"""You are rewriting a living document module. The user has requested: "{user_message}"

Standing Instruction for this module:
{standing_instruction}

Current module content:
{current_content}

"""
        
        if web_search_results:
            prompt += f"""Web search results (use these for factual accuracy):
{web_search_results}

"""
        
        prompt += """Your task:
1. Understand the user's intent
2. Rewrite the ENTIRE module content (never append or partially edit)
3. Maintain consistency with the standing instruction
4. Ensure the content is complete and coherent
5. If web search results were provided, use them to ensure factual accuracy

Return ONLY the new complete markdown content. Do not include any explanations or metadata."""
        
        return prompt
    
    @staticmethod
    def get_conversational_prompt(user_message: str, context: str = "") -> str:
        """Generate prompt for conversational responses"""
        prompt = f"""You are a helpful AI assistant helping users manage their living documents. The user sent this message: "{user_message}"

{context if context else ""}

Provide a helpful, friendly, and conversational response. If they're asking how to do something, explain it clearly. If it's a greeting, respond warmly. If it's a question, answer it helpfully. Be natural and conversational."""
        
        return prompt

