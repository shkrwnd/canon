"""
Document Rewrite Template

Template for document rewrite/editing prompts.
Handles selective and full edit scopes with validation error recovery.
"""

from typing import Dict, Any, List, Optional
import re
from .base import PromptTemplate


class DocumentRewriteTemplate(PromptTemplate):
    """Template for document rewrite prompts."""
    name = "document_rewrite"
    version = "v1"
    
    def __init__(self, edit_scope: Optional[str] = None):
        """
        Initialize template.
        
        Args:
            edit_scope: "selective" or "full" or None
        """
        self.edit_scope = edit_scope
    
    def render(self, policy_text: str, runtime: Dict[str, Any]) -> str:
        """Render document rewrite prompt."""
        user_message = runtime["user_message"]
        standing_instruction = runtime.get("standing_instruction", "")
        current_content = runtime.get("current_content", "")
        web_search_results = runtime.get("web_search_results")
        validation_errors = runtime.get("validation_errors")
        intent_statement = runtime.get("intent_statement")
        
        # Check if user_message is a confirmation
        confirmation_words = ["yes", "ok", "okay", "sure", "yeah", "yep", "proceed", "go ahead", "do it"]
        effective_request = user_message
        if intent_statement and user_message.lower().strip() in confirmation_words:
            effective_request = intent_statement
            task_note = f'Note: User confirmed with "{user_message}". The full intent is: {intent_statement}'
        else:
            task_note = ""
        
        # Build task
        task = f"""Update document based on user request. Request: "{effective_request}"
{task_note}

CRITICAL: Read the "Current Content" section below FIRST before making any changes.
Understand the existing structure, format, and content, then build upon it.

Standing Instruction: {standing_instruction}

=== CURRENT CONTENT (READ THIS FIRST) ===
{current_content}
=== END OF CURRENT CONTENT ===

{self._render_scope_instructions(user_message)}
{self._render_web_search_section(web_search_results)}
{self._render_validation_errors(validation_errors)}

IMPORTANT - Track Your Changes:
- As you make changes, be aware of what you're modifying:
  * Which sections did you update?
  * What specific information did you add, remove, or change?
  * Did you tailor existing content to new context (e.g., updated product recommendations for specific skin type)?
- This awareness will help ensure changes are accurate and complete
- Keep track mentally of: what was there → what changed → what's now there

Output Requirements:
- Pure markdown (NO HTML tags)
- Preserve ALL formatting: tables, links, images, code blocks, lists, headings
- Preserve ALL sections not mentioned in request
- Build upon existing content - don't replace it unless explicitly asked
- Match existing style, tone, and format
- **MANDATORY: If web search results were provided above, the document MUST end with a "## Sources" section**
- **The Sources section must list ALL URLs from the web search results in format: - [Title](URL)**
- Return ONLY markdown content (no explanations)
- Be aware of what you changed so you can accurately describe modifications if needed"""
        
        return f"""{policy_text}

TASK:
{task}"""
    
    def _render_scope_instructions(self, user_message: str) -> str:
        """Render scope-specific instructions."""
        if self.edit_scope == "selective":
            return f"""SELECTIVE EDIT - Build upon existing content:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

1. **Read the Current Content first**: Understand the structure, format, style, and existing information
2. **Understand the context**: What sections exist? What's the current format? What information is already there?
3. **Identify what needs to change**: Based on "{user_message}", determine what specific parts need updating
4. **Build upon existing content**: 
   - Keep the same structure, format, and style
   - Update only the relevant parts while preserving everything else
   - If user provides new context (e.g., "my skin is oily"), tailor the existing content to incorporate this context
   - Match the existing tone, formatting, and organization
5. **Preserve ALL other content exactly**: Everything not mentioned in the request stays the same

CRITICAL FOR SECTION REMOVAL:
- If user asks to remove specific sections (e.g., "remove Section 1, Section 2"), ONLY remove those exact sections
- Preserve ALL other sections completely unchanged
- Do NOT remove any sections that are not explicitly mentioned in the user's request
- Do NOT remove sections with similar names or content - only remove exact matches
- After removal, all remaining sections must appear in the same order and format

Examples:
- "replace heading" → change ONLY heading text, keep everything else
- "add to section X" → modify ONLY section X, preserve rest
- "remove Section 1, Section 2" → remove ONLY "Section 1" and "Section 2" headings and their content, preserve ALL other sections
- "my skin is oily" → update product recommendations in existing routine to suit oily skin, keep same structure
- "change title" → change ONLY title, preserve all content"""
        
        elif self.edit_scope == "full":
            return """FULL REWRITE - Preserve ALL sections and structure:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

- You may modify content extensively BUT must preserve:
  * ALL headings and sections (even if you rewrite their content)
  * Document structure and organization
  * All major sections mentioned in original
- DO NOT remove sections unless explicitly asked
- If user asks to remove specific sections, ONLY remove those exact sections and preserve all others
- If improving/updating: enhance content but keep all sections
- If restructuring: maintain all original sections, just reorganize
- CRITICAL: Every heading in original must appear in output (unless explicitly asked to remove)
- Build upon the existing content, don't replace it entirely unless explicitly asked"""
        
        else:
            return f"""Preserve ALL content unless explicitly asked to remove:
CRITICAL FIRST STEP: Read and understand the Current Content above before making any changes.

1. **Read the Current Content first**: Understand what's already there
2. **Understand the context**: Structure, format, existing information
3. **Identify what to change**: Based on "{user_message}", determine what needs updating
4. **Build upon existing content**: Update relevant parts while preserving structure and style
5. **Preserve everything else**: All content not mentioned in the request stays the same

CRITICAL FOR SECTION REMOVAL:
- If user asks to remove specific sections, ONLY remove those exact sections mentioned
- Preserve ALL other sections completely unchanged
- Do NOT remove sections that are not explicitly mentioned in the request"""
    
    def _render_web_search_section(self, web_search_results: Optional[str]) -> str:
        """Render web search results and attribution instructions."""
        if not web_search_results:
            return ""
        
        # Extract URLs and titles
        url_pattern = r'URL:\s*(https?://[^\s\n]+)'
        urls_found = re.findall(url_pattern, web_search_results)
        title_pattern = r'Title:\s*([^\n]+)'
        titles_found = re.findall(title_pattern, web_search_results)
        
        # Build sources list
        sources_list = []
        for i, url in enumerate(urls_found):
            title = titles_found[i] if i < len(titles_found) else "Source"
            sources_list.append(f"- [{title}]({url})")
        
        return f"""
Web Search Results:
{web_search_results}

================================================================================
MANDATORY - Web Search Source Attribution (CRITICAL - DO NOT SKIP):
================================================================================
Web search results have been provided above. You MUST include source attribution.

The web search results are formatted as:
Title: [Title]
URL: [URL]
Content: [Content]
---

REQUIRED STEPS (YOU MUST DO THIS):
1. Find ALL "URL:" lines in the web search results above
2. Extract the Title from the line immediately before each URL
3. Add a "## Sources" section at the VERY END of the document (after all other content)
4. Format each source as: - [Title](URL)
5. Include ALL URLs from the web search results, even if you only used part of the content

Expected Sources Section Format:
## Sources
{chr(10).join(sources_list[:5])}

CRITICAL RULES:
- The document output MUST end with a "## Sources" section
- The Sources section MUST be the last thing in the document
- You MUST include ALL URLs from the web search results
- DO NOT skip this step - it is mandatory
- If you skip this, the document is incomplete and invalid

VALIDATION: Before returning your response, check that your document ends with:
## Sources
- [Title](URL)
- [Title](URL)
...

If it doesn't, add it now.
================================================================================
"""
    
    def _render_validation_errors(self, validation_errors: Optional[List[str]]) -> str:
        """Render validation errors section."""
        if not validation_errors:
            return ""
        
        # Extract section names from error messages
        section_names = []
        for error in validation_errors:
            if "Lost" in error and "sections" in error:
                match = re.search(r':\s*([^.]+)', error)
                if match:
                    sections_text = match.group(1)
                    sections = [s.strip() for s in sections_text.split(',')]
                    sections = [s for s in sections if not re.match(r'and \d+ more', s)]
                    section_names.extend(sections)
        
        if section_names:
            unique_sections = []
            seen = set()
            for section in section_names:
                if section not in seen:
                    unique_sections.append(section)
                    seen.add(section)
            
            return f"""

CRITICAL - Previous attempt had validation issues:
{chr(10).join(validation_errors)}

You MUST fix these issues:
- The following sections were ACCIDENTALLY removed and MUST be restored:
{chr(10).join(f'  * {section}' for section in unique_sections)}
- These sections were NOT requested to be removed by the user
- Preserve ALL original headings and sections that were NOT explicitly requested to be removed
- Only remove the sections explicitly mentioned in the user's request
- Keep everything else completely intact"""
        else:
            return f"""

CRITICAL - Previous attempt had validation issues:
{chr(10).join(validation_errors)}

You MUST fix these issues:
- Restore ALL missing sections mentioned above (they were accidentally removed)
- Preserve ALL original headings and sections that were NOT requested to be removed
- Only remove the sections explicitly requested by the user
- Keep everything else completely intact"""
