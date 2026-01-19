"""
Prompt Templates Module

This module contains all prompt template classes, each in its own file
for better modularity and maintainability.
"""

from .base import PromptTemplate
from .intent_classification import IntentClassificationTemplate
from .agent_decision import AgentDecisionTemplate
from .document_rewrite import DocumentRewriteTemplate
from .conversational import ConversationalTemplate

__all__ = [
    "PromptTemplate",
    "IntentClassificationTemplate",
    "AgentDecisionTemplate",
    "DocumentRewriteTemplate",
    "ConversationalTemplate",
]
