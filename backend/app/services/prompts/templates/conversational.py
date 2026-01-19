"""
Conversational Template

Template for conversational prompts when no document operation is needed.
Handles web search results and location questions.
"""

from typing import Dict, Any, Optional
from .base import PromptTemplate
from ..utils import get_current_date_context


class ConversationalTemplate(PromptTemplate):
    """Template for conversational prompts."""
    name = "conversational"
    version = "v1"
    
    def __init__(self, has_web_search: bool = False):
        """
        Initialize template.
        
        Args:
            has_web_search: Whether web search results are available
        """
        self.has_web_search = has_web_search
    
    def render(self, policy_text: str, runtime: Dict[str, Any]) -> str:
        """Render conversational prompt."""
        user_message = runtime["user_message"]
        context = runtime.get("context", "")
        web_search_results = runtime.get("web_search_results")
        
        user_lower = user_message.lower()
        date_ctx = get_current_date_context()
        current_year = date_ctx["current_year"]
        current_date_str = date_ctx["current_date_str"]
        
        # Special handling for location questions
        if any(keyword in user_lower for keyword in ["where", "where did", "where is", "what did you"]):
            task = f"""User is asking about location/status of documents or changes.

Context from conversation history:
{context}
{self._render_web_search_section(web_search_results)}
User question: "{user_message}"

Provide a clear answer:
- If context mentions a document was created/updated, tell user the document name
- Reference specific document names from the context
- Be specific about what was done and where
- If you see "Recent document operations" in context, use that information
- If web search results are provided, use them to provide accurate, up-to-date information

Answer: Provide the information directly. If including a closing statement (e.g., "If you have any more questions..."), add 2-3 blank lines BEFORE the closing statement to visually separate the answer from the pleasantry."""
        else:
            if web_search_results:
                task = f"""=== WEB SEARCH COMPLETED ===
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

Answer now:"""
            else:
                task = f"""Helpful assistant for document management.

CURRENT USER QUESTION (answer this one): "{user_message}"

CRITICAL: Answer the question above. Chat history below is for context only - do not answer previous questions.

{self._render_context_section(context)}

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
  
  
  If you have any more questions or need assistance with something else, feel free to ask!"""
        
        return f"""{policy_text}

TASK:
{task}"""
    
    def _render_web_search_section(self, web_search_results: Optional[str]) -> str:
        """Render web search results section."""
        if web_search_results:
            return f"""

Web Search Results (use this information to answer the user's question):
{web_search_results}
"""
        return ""
    
    def _render_context_section(self, context: str) -> str:
        """Render context section."""
        if context:
            return f"Context: {context}\n"
        return ""
