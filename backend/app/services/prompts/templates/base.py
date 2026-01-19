"""
Base Template Class

Abstract base class for all prompt templates using the Template Method pattern.
"""

from typing import Dict, Any


class PromptTemplate:
    """
    Base template class. Subclasses implement render().
    
    Follows the Template Method pattern where the structure is defined
    in the base class and specific implementations are in subclasses.
    """
    name: str = "base"
    version: str = "v1"
    
    def render(self, policy_text: str, runtime: Dict[str, Any]) -> str:
        """
        Render template with policy and runtime data.
        
        Args:
            policy_text: Rendered policy text
            runtime: Runtime data (user_message, documents, etc.)
        
        Returns:
            Complete prompt string following the structured format:
            - ROLE
            - OBJECTIVE
            - INSTRUCTION PRIORITY
            - CONSTRAINTS
            - PROCESS
            - OUTPUT FORMAT
            - TASK
            - EXAMPLES
        """
        raise NotImplementedError
