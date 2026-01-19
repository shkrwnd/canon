"""
Prompt Architecture Module

This module provides a production-ready prompt management system using:
- Policy Pack: Centralized, stable rules
- Templates: Template Method pattern for prompt structures
- Builder: Assemble prompts from modular blocks
- Router: Strategy pattern for intent-based routing
- Schema Validation: Pydantic models for structured outputs
"""

from .blocks import Block, bullets, numbered
from .models import (
    IntentAction,
    DocumentTarget,
    IntentClassificationResult,
    AgentDecisionResult
)
from .policy import AgentPolicyPack, create_agent_policy_pack
from .templates import (
    PromptTemplate,
    IntentClassificationTemplate,
    AgentDecisionTemplate,
    DocumentRewriteTemplate,
    ConversationalTemplate
)
from .builder import PromptBuilder
from .router import TemplateRouter
from .utils import (
    get_current_date_context,
    build_documents_list,
    build_conversation_context
)
from .tools import (
    ToolName,
    ToolResult,
    ToolRegistry,
    create_default_tool_registry,
    available_tools_text
)

__all__ = [
    # Blocks
    "Block",
    "bullets",
    "numbered",
    # Models
    "IntentAction",
    "DocumentTarget",
    "IntentClassificationResult",
    "AgentDecisionResult",
    # Policy
    "AgentPolicyPack",
    "create_agent_policy_pack",
    # Templates
    "PromptTemplate",
    "IntentClassificationTemplate",
    "AgentDecisionTemplate",
    "DocumentRewriteTemplate",
    "ConversationalTemplate",
    # Builder
    "PromptBuilder",
    # Router
    "TemplateRouter",
    # Utils
    "get_current_date_context",
    "build_documents_list",
    "build_conversation_context",
    # Tools
    "ToolName",
    "ToolResult",
    "ToolRegistry",
    "create_default_tool_registry",
    "available_tools_text",
]
