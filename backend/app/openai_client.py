from typing import Dict, Any, Optional, Union
from openai import AzureOpenAI, OpenAI
from .config import settings

_client = None

def get_client() -> Union[OpenAI, AzureOpenAI]:
    """Get or create OpenAI client (lazy initialization) - supports both Azure OpenAI and direct OpenAI"""
    global _client
    if _client is None:
        # Prefer Azure OpenAI if configured
        if settings.azure_openai_api_key and settings.azure_openai_base_url:
            # Normalize the endpoint URL (remove trailing slash if present)
            endpoint = settings.azure_openai_base_url.rstrip('/')
            _client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=endpoint
            )
        elif settings.openai_api_key:
            # Fall back to direct OpenAI
            _client = OpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError("Either AZURE_OPENAI_API_KEY or OPENAI_API_KEY must be set. Please configure it in your .env file.")
    return _client

def get_model_name() -> str:
    """Get the model name to use - Azure OpenAI model or default"""
    if settings.azure_openai_api_key and settings.azure_openai_base_url:
        return settings.azure_openai_chat_model
    return "gpt-4o"  # Default for direct OpenAI


def get_agent_decision_prompt(user_message: str, modules: list, current_module: Optional[Dict] = None) -> str:
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
- If needs_web_search is true, provide search_query
- Provide conversational_response for non-edit messages (questions, greetings, general conversation) - this should be a natural, helpful response
- When resolving module names, match flexibly but accurately
- IMPORTANT: Be generous in interpreting edit intent - if there's any indication the user wants content changed, set should_edit to true"""
    
    return prompt


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


async def get_agent_decision(user_message: str, modules: list, current_module: Optional[Dict] = None) -> Dict[str, Any]:
    """Get agent decision on what to do"""
    prompt = get_agent_decision_prompt(user_message, modules, current_module)
    client = get_client()
    model_name = get_model_name()
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that helps users manage documents. You can have conversations and make decisions about editing. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.5
    )
    
    import json
    decision = json.loads(response.choices[0].message.content)
    return decision


async def rewrite_module_content(
    user_message: str,
    standing_instruction: str,
    current_content: str,
    web_search_results: Optional[str] = None
) -> str:
    """Rewrite module content based on user intent"""
    prompt = get_module_rewrite_prompt(user_message, standing_instruction, current_content, web_search_results)
    client = get_client()
    model_name = get_model_name()
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert editor that rewrites documents based on user intent. Return only the markdown content, no explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()


async def generate_conversational_response(user_message: str, context: str = "") -> str:
    """Generate a conversational response when no edit is needed"""
    client = get_client()
    model_name = get_model_name()
    
    prompt = f"""You are a helpful AI assistant helping users manage their living documents. The user sent this message: "{user_message}"

{context if context else ""}

Provide a helpful, friendly, and conversational response. If they're asking how to do something, explain it clearly. If it's a greeting, respond warmly. If it's a question, answer it helpfully. Be natural and conversational."""
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful, friendly assistant that helps users manage their documents. Respond naturally and conversationally."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()

