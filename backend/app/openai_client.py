from typing import Dict, Any, Optional
from openai import OpenAI
from .config import settings

_client = None

def get_client() -> OpenAI:
    """Get or create OpenAI client (lazy initialization)"""
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set. Please configure it in your .env file.")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_agent_decision_prompt(user_message: str, modules: list, current_module: Optional[Dict] = None) -> str:
    """Generate prompt for agent decision-making"""
    modules_list = "\n".join([f"- {m['name']} (id: {m['id']})" for m in modules])
    
    prompt = f"""You are an agentic editor for living documents. Your role is to:
1. Detect user intent from their message
2. Determine which module (if any) should be edited
3. Decide if web search is needed
4. Rewrite the entire module content (never append)

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
    "search_query": string or null
}

If should_edit is true, you must provide module_id. If needs_web_search is true, provide search_query."""
    
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
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that makes decisions about document editing. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
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
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert editor that rewrites documents based on user intent. Return only the markdown content, no explanations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()



