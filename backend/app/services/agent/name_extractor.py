"""
Document Name Extractor

Extracts document name from various sources with priority order.
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class DocumentNameExtractor:
    """Extracts document name from various sources with priority order"""
    
    @staticmethod
    def extract_name(decision: Dict[str, Any], user_message: str, documents_list: List[Dict]) -> str:
        """
        Extract document name with priority order:
        1. From decision (LLM-provided)
        2. From intent_statement
        3. From user message
        4. Fallback to generic name
        """
        # Priority 1: Use document_name from decision (most reliable - LLM should provide this)
        document_name = decision.get("document_name")
        
        # Priority 2: Extract from intent_statement (more flexible than hardcoded keywords)
        if not document_name:
            document_name = DocumentNameExtractor._extract_from_intent(decision.get("intent_statement", ""))
        
        # Priority 3: Extract from user message as last resort (simple noun extraction)
        if not document_name:
            document_name = DocumentNameExtractor._extract_from_user_message(user_message)
        
        # Priority 4: Fallback to generic name
        if not document_name or document_name == "New Document":
            document_name = f"Document {len(documents_list) + 1}"
            logger.warning(f"Using fallback document name: {document_name}")
        
        return document_name
    
    @staticmethod
    def _extract_from_intent(intent_statement: str) -> Optional[str]:
        """Extract name from intent statement"""
        if not intent_statement:
            return None
        
        intent_lower = intent_statement.lower()
        document_name = None
        
        # Pattern 1: "called X", "named X", "for X"
        if "called" in intent_lower or "named" in intent_lower or "for" in intent_lower:
            parts = intent_statement.split()
            for i, part in enumerate(parts):
                if part.lower() in ["called", "named", "for"] and i + 1 < len(parts):
                    document_name = " ".join(parts[i+1:]).strip('"\'.,')
                    # Remove common words like "document", "in", "this", "project"
                    document_name = document_name.replace("document", "").replace("in", "").replace("this", "").replace("project", "").strip()
                    if document_name:
                        logger.info(f"Extracted document name '{document_name}' from intent_statement")
                        break
        
        # Pattern 2: "create X" or "I'll create X"
        if not document_name:
            parts = intent_statement.split()
            for i, part in enumerate(parts):
                if part.lower() == "create" and i + 1 < len(parts):
                    # Take the next 1-3 words as potential document name
                    potential_name = " ".join(parts[i+1:i+4])
                    # Clean up common words
                    potential_name = potential_name.replace("document", "").replace("a", "").replace("new", "").replace("for", "").replace("in", "").replace("this", "").replace("project", "").strip()
                    if potential_name and len(potential_name) > 1:
                        document_name = potential_name
                        logger.info(f"Extracted document name '{document_name}' from intent_statement (create pattern)")
                        break
        
        return document_name
    
    @staticmethod
    def _extract_from_user_message(user_message: str) -> Optional[str]:
        """Extract name from user message (simple noun extraction)"""
        # Simple approach: look for nouns after action words
        user_words = user_message.split()
        action_words = ["add", "create", "make", "new", "my"]
        stop_words = ["my", "favorite", "the", "a", "an", "for", "to", "in", "with", "about"]
        
        for i, word in enumerate(user_words):
            word_lower = word.lower()
            # Look for action words or possessive patterns
            if word_lower in action_words and i + 1 < len(user_words):
                # Take the next 1-3 words as potential document name
                potential_name_words = []
                for j in range(i + 1, min(i + 4, len(user_words))):
                    next_word = user_words[j].lower()
                    # Stop if we hit another action word or common stop word
                    if next_word in action_words or next_word in stop_words:
                        break
                    potential_name_words.append(user_words[j])
                
                if potential_name_words:
                    document_name = " ".join(potential_name_words)
                    # Capitalize properly
                    document_name = " ".join([w.capitalize() for w in document_name.split()])
                    logger.info(f"Extracted document name '{document_name}' from user message")
                    return document_name
        
        return None

