"""
Prompt Builder - Assemble prompts from blocks and templates.

The Builder pattern allows for flexible prompt assembly while
maintaining the structured format.
"""

from typing import Dict, Any, List, Optional
from .blocks import Block
from .policy import AgentPolicyPack
from .templates import PromptTemplate


class PromptBuilder:
    """
    Builder for assembling prompts from blocks and templates.
    
    Follows the Builder pattern to allow fluent API for constructing prompts.
    """
    
    def __init__(
        self,
        policy: AgentPolicyPack,
        template: PromptTemplate,
        runtime: Dict[str, Any]
    ):
        """
        Initialize builder.
        
        Args:
            policy: Policy pack with rules
            template: Template for prompt structure
            runtime: Runtime data (user_message, documents, etc.)
        """
        self.policy = policy
        self.template = template
        self.runtime = runtime
        self.extra_blocks: List[Block] = []
        self.separator: str = "\n\n"
        self.task: Optional[str] = None
        self.examples: Optional[str] = None
        self.include_sections: Optional[List[str]] = None
    
    def add_block(self, title: str, body: str, priority: int = 100) -> "PromptBuilder":
        """
        Add an extra block to the prompt.
        
        Args:
            title: Block title
            body: Block content
            priority: Block priority (lower = higher priority)
        
        Returns:
            Self for method chaining
        """
        self.extra_blocks.append(Block(title, body, priority))
        return self
    
    def with_task(self, task: str) -> "PromptBuilder":
        """
        Set the task description.
        
        Args:
            task: Task description
        
        Returns:
            Self for method chaining
        """
        self.task = task
        return self
    
    def with_examples(self, examples: str) -> "PromptBuilder":
        """
        Set examples.
        
        Args:
            examples: Examples text
        
        Returns:
            Self for method chaining
        """
        self.examples = examples
        return self
    
    def with_sections(self, sections: List[str]) -> "PromptBuilder":
        """
        Specify which policy sections to include.
        
        Args:
            sections: List of section names to include
        
        Returns:
            Self for method chaining
        """
        self.include_sections = sections
        return self
    
    def with_documents(self, documents: list) -> "PromptBuilder":
        """
        Add document context to runtime.
        
        Args:
            documents: List of document dictionaries
        
        Returns:
            Self for method chaining
        """
        self.runtime["documents"] = documents
        return self
    
    def with_intent_metadata(self, metadata: Dict) -> "PromptBuilder":
        """
        Add intent metadata to runtime.
        
        Args:
            metadata: Intent metadata dictionary
        
        Returns:
            Self for method chaining
        """
        self.runtime["intent_metadata"] = metadata
        return self
    
    def with_project_context(self, context: Dict) -> "PromptBuilder":
        """
        Add project context to runtime.
        
        Args:
            context: Project context dictionary
        
        Returns:
            Self for method chaining
        """
        self.runtime["project_context"] = context
        return self
    
    def with_chat_history(self, history: List[Dict]) -> "PromptBuilder":
        """
        Add chat history to runtime.
        
        Args:
            history: Chat history list
        
        Returns:
            Self for method chaining
        """
        self.runtime["chat_history"] = history
        return self
    
    def with_web_search_results(self, results: str) -> "PromptBuilder":
        """
        Add web search results to runtime.
        
        Args:
            results: Web search results string
        
        Returns:
            Self for method chaining
        """
        self.runtime["web_search_results"] = results
        return self
    
    def build(self) -> str:
        """
        Build the final prompt.
        
        Returns:
            Complete prompt string following the structured format
        """
        # Render policy with specified sections, task, and examples
        policy_text = self.policy.render(
            include_sections=self.include_sections,
            task=self.task,
            examples=self.examples,
            separator=self.separator
        )
        
        # Add extra blocks if any
        if self.extra_blocks:
            extra_blocks_sorted = sorted(self.extra_blocks, key=lambda x: x.priority)
            extras_text = self.separator.join(b.render() for b in extra_blocks_sorted)
            policy_text = policy_text + self.separator + extras_text
        
        # Render template with policy text and runtime data
        return self.template.render(policy_text, self.runtime)
