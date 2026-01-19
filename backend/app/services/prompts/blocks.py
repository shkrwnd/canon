"""
Block structure for modular prompt assembly.

Blocks are immutable components that can be assembled into prompts.
They follow a clear structure with title, body, and priority for ordering.
"""

from dataclasses import dataclass
from typing import List


def bullets(items: List[str]) -> str:
    """Format list as bullet points."""
    return "\n".join(f"- {x}" for x in items)


def numbered(items: List[str]) -> str:
    """Format list as numbered items."""
    return "\n".join(f"{i+1}. {x}" for i, x in enumerate(items))


@dataclass(frozen=True)
class Block:
    """
    Immutable block for prompt assembly.
    
    Blocks represent sections of a prompt with:
    - title: Section header (e.g., "ROLE", "CONSTRAINTS")
    - body: Section content
    - priority: Lower numbers render first (for ordering)
    """
    title: str
    body: str
    priority: int = 0
    
    def render(self) -> str:
        """
        Render block as formatted text.
        
        Returns:
            Formatted block with title and body.
        """
        if not self.title:
            return self.body.strip()
        return f"{self.title}:\n{self.body}".strip()
