"""
Document Validator - Action-bound validators for document operations.

This module provides validators for different document operations,
following the Cursor-style strategy of validating structure, not reasoning.
"""
import re
from typing import List, Tuple, Optional, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of document validation with change tracking"""
    
    def __init__(
        self, 
        is_valid: bool, 
        errors: List[str], 
        warnings: List[str] = None,
        change_details: Optional[Dict[str, Any]] = None
    ):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings or []
        self.change_details = change_details or {}
    
    def __bool__(self):
        return self.is_valid
    
    def __str__(self):
        if self.is_valid:
            return "Validation passed"
        return f"Validation failed: {', '.join(self.errors)}"
    
    def get_intent_checkable_errors(self) -> List[Dict[str, Any]]:
        """
        Extract errors that might be intentional based on user request.
        Returns list of error details that can be checked against user intent.
        """
        checkable = []
        
        for error in self.errors:
            error_lower = error.lower()
            
            # Section removal errors
            if "lost" in error_lower and "sections" in error_lower:
                checkable.append({
                    "type": "section_removal",
                    "error": error,
                    "missing_sections": self.change_details.get("missing_sections", [])
                })
            
            # Structural change errors
            elif "structure significantly changed" in error_lower:
                checkable.append({
                    "type": "structural_change",
                    "error": error,
                    "original_section_count": self.change_details.get("original_section_count", 0),
                    "new_section_count": self.change_details.get("new_section_count", 0)
                })
            
            # Content reduction errors
            elif ("too short" in error_lower or 
                  ("lost" in error_lower and "% of content" in error)):
                checkable.append({
                    "type": "content_reduction",
                    "error": error,
                    "original_length": self.change_details.get("original_length", 0),
                    "new_length": self.change_details.get("new_length", 0),
                    "reduction_pct": self.change_details.get("reduction_pct", 0)
                })
        
        return checkable
    
    def has_intent_checkable_errors(self) -> bool:
        """Check if there are any errors that should be validated against user intent"""
        return len(self.get_intent_checkable_errors()) > 0


class DocumentValidator:
    """Validators for document operations"""
    
    # Common placeholders that should not appear in final output
    PLACEHOLDERS = [
        "url-to-image",
        "TODO",
        "FIXME",
        "[placeholder]",
        "[INSERT",
        "PLACEHOLDER",
        "XXX",
        "TBD"
    ]
    
    @staticmethod
    def is_valid_markdown(content: str) -> bool:
        """
        Basic markdown validation - checks for common issues.
        Note: This is not a full markdown parser, just basic checks.
        """
        if not content:
            return True  # Empty content is valid
        
        # Check for unclosed code blocks
        code_block_count = content.count('```')
        if code_block_count % 2 != 0:
            return False
        
        # Check for malformed links (basic check)
        # Links should be [text](url) format
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)
        for text, url in links:
            if not text.strip() or not url.strip():
                return False
        
        # Check for malformed images (basic check)
        # Images should be ![alt](url) format
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        images = re.findall(image_pattern, content)
        for alt, url in images:
            if not url.strip():
                return False
        
        return True
    
    @staticmethod
    def extract_headings(content: str) -> List[str]:
        """Extract all markdown headings from content"""
        heading_pattern = r'^#{1,6}\s+(.+)$'
        headings = []
        for line in content.split('\n'):
            match = re.match(heading_pattern, line.strip())
            if match:
                headings.append(match.group(1).strip())
        return headings
    
    @staticmethod
    def extract_links(content: str) -> List[Tuple[str, str]]:
        """Extract all markdown links from content"""
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        return re.findall(link_pattern, content)
    
    @staticmethod
    def extract_images(content: str) -> List[Tuple[str, str]]:
        """Extract all markdown images from content"""
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        return re.findall(image_pattern, content)
    
    @staticmethod
    def validate_rewrite(
        new_content: str,
        original_content: str,
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate rewritten document content.
        
        Args:
            new_content: The new document content
            original_content: The original document content
            strict: If True, enforce stricter validation rules
        
        Returns:
            ValidationResult with is_valid, errors, warnings, and change_details
        """
        errors = []
        warnings = []
        
        # Track changes for intent validation
        original_headings = set(DocumentValidator.extract_headings(original_content))
        new_headings = set(DocumentValidator.extract_headings(new_content))
        missing_sections = list(original_headings - new_headings)
        added_sections = list(new_headings - original_headings)
        
        original_length = len(original_content) if original_content else 0
        new_length = len(new_content) if new_content else 0
        reduction_pct = 0
        if original_length > 0:
            reduction_pct = ((original_length - new_length) / original_length) * 100
        
        # Check 1: Is it valid markdown?
        if not DocumentValidator.is_valid_markdown(new_content):
            errors.append("Output is not valid markdown (unclosed code blocks, malformed links/images)")
        
        # Check 2: Did we remove placeholders?
        for placeholder in DocumentValidator.PLACEHOLDERS:
            if placeholder in new_content:
                errors.append(f"Found placeholder in output: {placeholder}")
        
        # Check 3: Did we preserve structure? (ERROR if significant sections lost)
        if missing_sections and original_headings:
            # Calculate percentage of sections lost
            sections_lost_pct = len(missing_sections) / len(original_headings) * 100
            
            # If we lost more than 10% of sections, that's an error (content was likely accidentally removed)
            if sections_lost_pct > 10:
                errors.append(
                    f"Lost {len(missing_sections)} sections ({sections_lost_pct:.1f}% of document): "
                    f"{', '.join(missing_sections[:5])}"
                    + (f" and {len(missing_sections) - 5} more" if len(missing_sections) > 5 else "")
                    + ". This suggests content was accidentally removed."
                )
            else:
                # Less than 10% lost - warning but not error (might be intentional)
                warnings.append(f"Missing sections from original: {', '.join(missing_sections[:3])}")
        
        # Check 3.5: Section count validation (additional safety check)
        if original_headings and new_headings:
            # If we have significantly fewer sections, that's suspicious
            if len(new_headings) < len(original_headings) * 0.8:  # Lost more than 20% of sections
                errors.append(
                    f"Document structure significantly changed: "
                    f"Original had {len(original_headings)} sections, new has {len(new_headings)} sections. "
                    f"This suggests content was accidentally removed."
                )
        
        # Check 4: Is content reasonable length?
        # If we lost more than 90% of content, something is wrong
        if original_content and len(new_content) < len(original_content) * 0.1:
            errors.append(
                f"Content seems too short - lost {100 - (len(new_content) / len(original_content) * 100):.1f}% of content. "
                "This may indicate content was accidentally removed."
            )
        
        # Check 5: Did we preserve links? (warnings)
        original_links = set(DocumentValidator.extract_links(original_content))
        new_links = set(DocumentValidator.extract_links(new_content))
        missing_links = original_links - new_links
        if missing_links and strict:
            warnings.append(f"Missing links from original: {len(missing_links)} links")
        
        # Check 6: Did we preserve images? (warnings)
        original_images = set(DocumentValidator.extract_images(original_content))
        new_images = set(DocumentValidator.extract_images(new_content))
        missing_images = original_images - new_images
        if missing_images and strict:
            warnings.append(f"Missing images from original: {len(missing_images)} images")
        
        # Build change details for intent validation
        change_details = {
            "missing_sections": missing_sections,
            "added_sections": added_sections,
            "original_section_count": len(original_headings),
            "new_section_count": len(new_headings),
            "original_length": original_length,
            "new_length": new_length,
            "reduction_pct": reduction_pct
        }
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            change_details=change_details
        )
    
    @staticmethod
    def validate_create(
        document_name: str,
        content: str
    ) -> ValidationResult:
        """
        Validate new document creation.
        
        Args:
            document_name: The document name
            content: The document content
        
        Returns:
            ValidationResult with is_valid and errors
        """
        errors = []
        
        # Check 1: Document name is required
        if not document_name or not document_name.strip():
            errors.append("Document name is required and cannot be empty")
        
        # Check 2: Document name is reasonable length
        if document_name and len(document_name.strip()) > 200:
            errors.append("Document name is too long (max 200 characters)")
        
        # Check 3: Content is valid markdown
        if content and not DocumentValidator.is_valid_markdown(content):
            errors.append("Content is not valid markdown")
        
        # Check 4: No placeholders in new content
        if content:
            for placeholder in DocumentValidator.PLACEHOLDERS:
                if placeholder in content:
                    errors.append(f"Found placeholder in new document: {placeholder}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    @staticmethod
    def validate_links(content: str) -> ValidationResult:
        """
        Validate all links in document content.
        
        Returns:
            ValidationResult with list of broken/invalid links
        """
        errors = []
        links = DocumentValidator.extract_links(content)
        
        broken_links = []
        for text, url in links:
            url = url.strip()
            # Check if URL is empty or placeholder
            if not url or url in DocumentValidator.PLACEHOLDERS:
                broken_links.append(f"[{text}]({url})")
            # Check if URL looks valid (basic check)
            elif not (url.startswith('http://') or url.startswith('https://') or url.startswith('/') or url.startswith('#')):
                # Allow relative URLs and anchors
                if not (url.startswith('./') or url.startswith('../') or url.startswith('mailto:')):
                    broken_links.append(f"[{text}]({url})")
        
        if broken_links:
            errors.append(f"Found {len(broken_links)} broken or invalid links: {', '.join(broken_links[:5])}")
        
        return ValidationResult(
            is_valid=len(broken_links) == 0,
            errors=errors if broken_links else []
        )
    
    @staticmethod
    def validate_images(content: str) -> ValidationResult:
        """
        Validate all images in document content.
        
        Returns:
            ValidationResult with list of broken/invalid image URLs
        """
        errors = []
        images = DocumentValidator.extract_images(content)
        
        broken_images = []
        for alt, url in images:
            url = url.strip()
            # Check if URL is empty or placeholder
            if not url or url in DocumentValidator.PLACEHOLDERS:
                broken_images.append(f"![{alt}]({url})")
        
        if broken_images:
            errors.append(f"Found {len(broken_images)} broken or placeholder images: {', '.join(broken_images[:5])}")
        
        return ValidationResult(
            is_valid=len(broken_images) == 0,
            errors=errors if broken_images else []
        )

