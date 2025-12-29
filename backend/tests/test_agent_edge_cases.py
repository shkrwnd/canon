"""
Agent Edge Case Testing Script

This script tests the agent on various edge cases and generates a detailed report.
It creates a project and test documents before running tests.

Usage:
    python -m pytest backend/tests/test_agent_edge_cases.py -v
    OR
    python backend/tests/test_agent_edge_cases.py
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Note: conftest imports are only needed for standalone execution
# They're imported conditionally in the __main__ block


@dataclass
class TestCase:
    """Represents a single test case"""
    name: str
    message: str
    category: str
    expected_intent: Optional[str] = None
    expected_web_search: Optional[bool] = None
    expected_should_edit: Optional[bool] = None
    expected_should_create: Optional[bool] = None
    expected_contains: Optional[List[str]] = None
    expected_not_contains: Optional[List[str]] = None
    description: str = ""
    requires_document: Optional[str] = None  # Document name that must exist for this test
    # LLM-based document validation (optional)
    validate_document_content: bool = False  # Enable document content validation
    validation_requirements: Optional[str] = None  # What to check (e.g., "preserves all sections", "contains latest version")
    validation_critical: bool = False  # If True, test fails if validation fails


@dataclass
class TestResult:
    """Represents the result of a test case"""
    test_case: TestCase
    passed: bool
    response_status: int
    actual_intent: Optional[str] = None
    actual_web_search: Optional[bool] = None
    actual_should_edit: Optional[bool] = None
    actual_should_create: Optional[bool] = None
    response_content: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    decision: Optional[Dict[str, Any]] = None


@dataclass
class TestReport:
    """Represents the complete test report"""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    results: List[TestResult]
    summary: Dict[str, Any]


class DocumentValidator:
    """Validates document content using LLM when needed"""
    
    def __init__(self, llm_service: Optional[Any] = None):
        """
        Initialize validator
        
        Args:
            llm_service: Optional LLMService instance (creates one if None)
        """
        self._llm_service = llm_service
        self._validation_cache = {}  # Cache validation results
    
    @property
    def llm_service(self):
        """Lazy-load LLM service (only created when needed)"""
        if self._llm_service is None:
            # Import here to avoid circular dependencies and only when needed
            import sys
            from pathlib import Path
            
            # Ensure backend is in path
            backend_dir = Path(__file__).parent.parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            
            from app.clients.llm_providers.factory import LLMProviderFactory
            from app.services.llm_service import LLMService
            
            provider = LLMProviderFactory.create_provider()
            self._llm_service = LLMService(provider)
        
        return self._llm_service
    
    async def validate(
        self,
        document_content: str,
        user_request: str,
        requirements: str,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate document content against requirements
        
        Args:
            document_content: Document content to validate
            user_request: Original user request
            requirements: Validation requirements
            cache_key: Optional cache key to avoid re-validating same content
        
        Returns:
            Dict with 'passed' (bool), 'reason' (str), 'issues' (list)
        """
        # Check cache first
        if cache_key and cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        # Build validation prompt
        prompt = f"""Validate if the document meets these requirements:

REQUIREMENTS: {requirements}

ORIGINAL REQUEST: {user_request}

DOCUMENT CONTENT:
{document_content}

Respond with JSON only:
{{
    "passed": true/false,
    "reason": "brief explanation",
    "issues": ["specific issues if any"]
}}"""

        messages = [
            {
                "role": "system",
                "content": "You are a test validator. Analyze the document and respond with valid JSON only. Be strict but fair."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            # Use the LLM service with rate limiting
            service = self.llm_service
            async with service._semaphore:  # Respect rate limiting
                response = await service.provider.chat_completion(
                    messages=messages,
                    temperature=0.1,  # Low temperature for consistency
                    response_format={"type": "json_object"} if service.provider.supports_json_mode() else None
                )
            
            result = json.loads(response)
            validation_result = {
                "passed": result.get("passed", False),
                "reason": result.get("reason", "No reason provided"),
                "issues": result.get("issues", [])
            }
            
            # Cache result
            if cache_key:
                self._validation_cache[cache_key] = validation_result
            
            return validation_result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM validation error: {e}")
            return {
                "passed": False,
                "reason": f"Validation error: {str(e)}",
                "issues": []
            }
    
    def clear_cache(self):
        """Clear validation cache"""
        self._validation_cache.clear()


class AgentTester:
    """Test harness for agent edge cases"""
    
    def __init__(self, client: TestClient, auth_token: str, project_id: int):
        self.client = client
        self.auth_token = auth_token
        self.project_id = project_id
        self.headers = {"Authorization": f"Bearer {auth_token}"}
        self.chat_id: Optional[int] = None
        self.documents: Dict[str, int] = {}  # Map document name to document ID
        self._validator: Optional[DocumentValidator] = None  # Lazy initialization
    
    @property
    def validator(self) -> DocumentValidator:
        """Lazy-load validator (only created when needed)"""
        if self._validator is None:
            self._validator = DocumentValidator()
        return self._validator
    
    def setup_test_environment(self):
        """Create test documents before running tests"""
        print("\n" + "="*80)
        print("Setting up test environment...")
        print("="*80)
        
        # Define test documents to create
        test_documents = [
            {
                "name": "Python Guide",
                "content": "# Python Guide\n\nPython is a high-level programming language.\n\n## Features\n- Easy to learn\n- Versatile\n- Large community",
                "description": "Main Python guide document"
            },
            {
                "name": "Python guide",  # Different case for testing
                "content": "# Python guide\n\nThis is a lowercase version.",
                "description": "Lowercase Python guide for case-insensitive testing"
            },
            {
                "name": "Latest Python Features",
                "content": "# Latest Python Features\n\nThis document discusses the latest features in Python.",
                "description": "Document about latest features for web search testing"
            },
            {
                "name": "TestDoc",
                "content": "# Test Document\n\nThis is a test document.",
                "description": "Test document for duplicate name testing"
            },
            {
                "name": "Recipes",
                "content": "# Recipes\n\n## Breakfast\n- Pancakes\n- Waffles",
                "description": "Recipes document for content testing"
            },
        ]
        
        # Create documents
        created_count = 0
        for doc_data in test_documents:
            try:
                response = self.client.post(
                    "/api/documents",
                    json={
                        "name": doc_data["name"],
                        "project_id": self.project_id,
                        "content": doc_data["content"],
                        "standing_instruction": ""
                    },
                    headers=self.headers
                )
                
                if response.status_code == 201:
                    doc_id = response.json()["id"]
                    self.documents[doc_data["name"]] = doc_id
                    created_count += 1
                    print(f"  ✓ Created document: {doc_data['name']} (ID: {doc_id})")
                else:
                    print(f"  ✗ Failed to create document: {doc_data['name']} - {response.status_code}")
                    if response.status_code == 409:  # Duplicate
                        # Try to get existing document
                        docs_response = self.client.get(
                            f"/api/projects/{self.project_id}/documents",
                            headers=self.headers
                        )
                        if docs_response.status_code == 200:
                            for doc in docs_response.json():
                                if doc["name"] == doc_data["name"]:
                                    self.documents[doc_data["name"]] = doc["id"]
                                    print(f"  → Using existing document: {doc_data['name']} (ID: {doc['id']})")
                                    break
            except Exception as e:
                print(f"  ✗ Error creating document {doc_data['name']}: {e}")
        
        print(f"\nCreated/Found {created_count} test documents")
        print("="*80 + "\n")
    
    def get_test_cases(self) -> List[TestCase]:
        """Define all edge case test cases"""
        return [
            # Intent Classification Edge Cases
            TestCase(
                name="General Knowledge Question - Current Info",
                message="who is the current president of US",
                category="intent_classification",
                expected_intent="conversation",
                expected_web_search=True,
                expected_should_edit=False,
                expected_should_create=False,
                expected_not_contains=["I will search", "I will look up", "Let me search"],
                description="Should classify as conversation and trigger web search, not say 'I will search'"
            ),
            TestCase(
                name="General Knowledge Question - Historical",
                message="who was the first president of US",
                category="intent_classification",
                expected_intent="conversation",
                expected_web_search=True,
                expected_should_edit=False,
                expected_should_create=False,
                description="Should classify as conversation and trigger web search"
            ),
            TestCase(
                name="Question with Action Word - Location",
                message="where did you make the changes",
                category="intent_classification",
                expected_intent="conversation",
                expected_web_search=False,
                expected_should_edit=False,
                expected_should_create=False,
                description="Should classify as conversation (question), not edit action"
            ),
            TestCase(
                name="Confirmation Response - Yes",
                message="yes",
                category="intent_classification",
                expected_intent="conversation",  # Will depend on context
                description="Should handle confirmation based on previous context"
            ),
            TestCase(
                name="Create Script Request",
                message="create a script for that",
                category="intent_classification",
                expected_intent="create",
                expected_should_create=True,
                expected_should_edit=False,
                description="Should classify as create, not conversation"
            ),
            TestCase(
                name="Save It Request",
                message="save it",
                category="intent_classification",
                expected_intent="edit",
                expected_should_edit=True,
                expected_should_create=False,
                description="Should classify as edit (save action), not conversation"
            ),
            
            # Web Search Trigger Edge Cases
            TestCase(
                name="Latest Information Request - Edit",
                message="edit the document about the latest Python features to be more verbose",
                category="web_search_trigger",
                expected_web_search=True,
                expected_should_edit=True,
                requires_document="Latest Python Features",
                validate_document_content=True,
                validation_requirements="Verify that the document contains more verbose descriptions of the latest Python features. The content should be expanded with more detailed explanations while maintaining accuracy about current Python features.",
                validation_critical=False,  # Warning only - making verbose is subjective
                description="Should trigger web search even for 'make verbose' if document is about 'latest'"
            ),
            TestCase(
                name="Latest Information Request - Add",
                message="add the latest Python version to the Python Guide document",
                category="web_search_trigger",
                expected_web_search=True,
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains information about the latest Python version (should be 3.12 or later as of 2024) and that this information is accurate and well-integrated into the document.",
                validation_critical=True,
                description="Should trigger web search for 'latest' information"
            ),
            TestCase(
                name="Current Year Query",
                message="what are the latest US administration changes in December",
                category="web_search_trigger",
                expected_web_search=True,
                expected_intent="conversation",
                description="Should trigger web search and infer most recent December"
            ),
            TestCase(
                name="Month-Only Query",
                message="what happened in January",
                category="web_search_trigger",
                expected_web_search=True,
                expected_intent="conversation",
                description="Should trigger web search and infer most recent January"
            ),
            
            # Document Operation Edge Cases
            TestCase(
                name="Edit Existing Document",
                message="edit the Python Guide and add information about data types",
                category="document_operations",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains information about Python data types (like int, str, list, dict, etc.) and that this information is well-integrated. All original sections should be preserved.",
                validation_critical=True,
                description="Should successfully edit an existing document"
            ),
            TestCase(
                name="Edit Non-Existent Document",
                message="edit the document called NonExistentDoc and add new content",
                category="document_operations",
                expected_should_edit=True,
                description="Should recognize edit intent even when document doesn't exist (will handle gracefully)"
            ),
            TestCase(
                name="Create Duplicate Document",
                message="create a document called TestDoc",
                category="document_operations",
                expected_should_edit=True,  # When duplicate exists, agent should edit instead
                expected_should_create=False,
                description="Should recognize duplicate and edit existing document instead of creating"
            ),
            TestCase(
                name="Vague Edit Request",
                message="update it",
                category="document_operations",
                description="Should handle vague requests (may need clarification)"
            ),
            TestCase(
                name="Edit with Web Search - Source Links",
                message="edit the Python Guide and add the latest Python version",
                category="document_operations",
                expected_web_search=True,
                expected_should_edit=True,
                expected_contains=["## Sources"],
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains a '## Sources' section with properly formatted URLs, that the sources are relevant to Python version information, and that the latest Python version information is accurate and well-integrated.",
                validation_critical=True,
                description="Should include source links when web search is performed"
            ),
            
            # Conversational Response Edge Cases
            TestCase(
                name="Greeting",
                message="hi",
                category="conversational_response",
                expected_intent="conversation",
                expected_web_search=False,
                description="Should respond conversationally without web search"
            ),
            TestCase(
                name="Question About Documents",
                message="what documents do I have",
                category="conversational_response",
                expected_intent="conversation",
                expected_web_search=False,
                description="Should answer about documents without web search"
            ),
            TestCase(
                name="Question About Document Content",
                message="what's in the Python Guide",
                category="conversational_response",
                expected_intent="conversation",
                expected_web_search=False,
                requires_document="Python Guide",
                description="Should answer about document content without web search"
            ),
            TestCase(
                name="Multi-Turn Question",
                message="when was he born",
                category="conversational_response",
                expected_intent="conversation",
                expected_web_search=True,
                description="Should use context from previous messages"
            ),
            
            # Error Handling Edge Cases
            TestCase(
                name="Empty Message",
                message="",
                category="error_handling",
                description="Should handle empty message gracefully"
            ),
            TestCase(
                name="Very Long Message",
                message="a" * 10000,
                category="error_handling",
                description="Should handle very long messages"
            ),
            TestCase(
                name="Special Characters",
                message="!@#$%^&*()_+-=[]{}|;':\",./<>?",
                category="error_handling",
                description="Should handle special characters"
            ),
            
            # Edge Cases for Intent Ambiguity
            TestCase(
                name="Ambiguous Request - Could Be Edit or Create",
                message="make a new document about Python",
                category="intent_ambiguity",
                expected_should_create=True,
                expected_should_edit=False,
                description="Should prioritize 'new document' keywords and create, not edit existing documents"
            ),
            TestCase(
                name="Question with Document Reference",
                message="what's in the Python Guide",
                category="intent_ambiguity",
                expected_intent="conversation",
                expected_should_edit=False,
                requires_document="Python Guide",
                description="Should classify as conversation (question), not edit"
            ),
        ]
    
    def create_project_if_needed(self) -> int:
        """Create a test project if needed"""
        # Try to get existing projects
        response = self.client.get("/api/projects", headers=self.headers)
        if response.status_code == 200 and response.json():
            return response.json()[0]["id"]
        
        # Create a new project
        response = self.client.post(
            "/api/projects",
            json={"name": "Agent Test Project", "description": "Test project for agent edge cases"},
            headers=self.headers
        )
        if response.status_code == 201:
            return response.json()["id"]
        raise Exception(f"Failed to create project: {response.text}")
    
    def run_test_case(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        start_time = time.time()
        
        try:
            # Prepare request
            request_data = {
                "message": test_case.message,
                "project_id": self.project_id,
            }
            if self.chat_id:
                request_data["chat_id"] = self.chat_id
            
            # If test requires a specific document, add document_id if available
            if test_case.requires_document and test_case.requires_document in self.documents:
                # Don't set document_id - let agent resolve by name
                # But we know the document exists
                pass
            
            # Make API call
            response = self.client.post(
                "/api/agent/act",
                json=request_data,
                headers=self.headers
            )
            
            execution_time = time.time() - start_time
            response_status = response.status_code
            
            # Parse response
            if response_status == 200:
                response_data = response.json()
                decision = response_data.get("agent_decision", {})
                chat_message = response_data.get("chat_message", {})
                response_content = chat_message.get("content", "")
                web_search_performed = response_data.get("web_search_performed", False)
                
                # Extract actual values
                actual_intent = decision.get("intent_type")
                actual_should_edit = decision.get("should_edit", False)
                actual_should_create = decision.get("should_create", False)
                
                # Validate expectations
                passed = True
                error_parts = []
                
                if test_case.expected_intent and actual_intent != test_case.expected_intent:
                    passed = False
                    error_parts.append(f"Intent mismatch: expected '{test_case.expected_intent}', got '{actual_intent}'")
                
                if test_case.expected_web_search is not None and web_search_performed != test_case.expected_web_search:
                    passed = False
                    error_parts.append(f"Web search mismatch: expected {test_case.expected_web_search}, got {web_search_performed}")
                
                if test_case.expected_should_edit is not None and actual_should_edit != test_case.expected_should_edit:
                    passed = False
                    error_parts.append(f"Should edit mismatch: expected {test_case.expected_should_edit}, got {actual_should_edit}")
                
                if test_case.expected_should_create is not None and actual_should_create != test_case.expected_should_create:
                    passed = False
                    error_parts.append(f"Should create mismatch: expected {test_case.expected_should_create}, got {actual_should_create}")
                
                # Check for expected/not expected content
                if test_case.expected_contains:
                    for expected_text in test_case.expected_contains:
                        if expected_text.lower() not in response_content.lower():
                            passed = False
                            error_parts.append(f"Expected content not found: '{expected_text}'")
                
                if test_case.expected_not_contains:
                    for not_expected_text in test_case.expected_not_contains:
                        if not_expected_text.lower() in response_content.lower():
                            passed = False
                            error_parts.append(f"Unexpected content found: '{not_expected_text}'")
                
                # LLM-based document validation (only if enabled and document exists)
                llm_validation_result = None
                document = response_data.get("document")
                document_content = document.get("content") if document else None
                
                if (test_case.validate_document_content and 
                    test_case.validation_requirements and 
                    document_content):
                    
                    # Run async validation
                    import asyncio
                    import hashlib
                    
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Create cache key from content hash (avoid re-validating same content)
                    cache_key = hashlib.md5(
                        f"{test_case.message}:{test_case.validation_requirements}:{document_content[:100]}".encode()
                    ).hexdigest()
                    
                    llm_validation_result = loop.run_until_complete(
                        self.validator.validate(
                            document_content=document_content,
                            user_request=test_case.message,
                            requirements=test_case.validation_requirements,
                            cache_key=cache_key
                        )
                    )
                    
                    # Check validation result
                    if not llm_validation_result.get("passed", False):
                        if test_case.validation_critical:
                            passed = False
                            error_parts.append(
                                f"Document validation failed: {llm_validation_result.get('reason', 'Unknown')}. "
                                f"Issues: {', '.join(llm_validation_result.get('issues', []))}"
                            )
                        else:
                            # Non-critical: log but don't fail test
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(
                                f"Document validation warning for '{test_case.name}': "
                                f"{llm_validation_result.get('reason', 'Unknown')}"
                            )
                
                # Update chat_id for multi-turn conversations
                if "chat_id" in response_data:
                    self.chat_id = response_data["chat_id"]
                
                # Include LLM validation result in decision metadata
                if llm_validation_result:
                    decision = {**decision, "llm_validation": llm_validation_result}
                
                return TestResult(
                    test_case=test_case,
                    passed=passed,
                    response_status=response_status,
                    actual_intent=actual_intent,
                    actual_web_search=web_search_performed,
                    actual_should_edit=actual_should_edit,
                    actual_should_create=actual_should_create,
                    response_content=response_content[:500],  # Truncate for report
                    error_message="; ".join(error_parts) if error_parts else None,
                    execution_time=execution_time,
                    decision=decision
                )
            else:
                return TestResult(
                    test_case=test_case,
                    passed=False,
                    response_status=response_status,
                    error_message=f"API returned status {response_status}: {response.text[:200]}",
                    execution_time=time.time() - start_time
                )
        
        except Exception as e:
            return TestResult(
                test_case=test_case,
                passed=False,
                response_status=0,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
    
    def run_all_tests(self) -> TestReport:
        """Run all test cases and generate report"""
        # Setup test environment first
        self.setup_test_environment()
        
        test_cases = self.get_test_cases()
        results = []
        
        print(f"\n{'='*80}")
        print(f"Running {len(test_cases)} edge case tests...")
        print(f"{'='*80}\n")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] Testing: {test_case.name}")
            result = self.run_test_case(test_case)
            results.append(result)
            
            status_icon = "✓" if result.passed else "✗"
            print(f"  {status_icon} {test_case.category} - {result.execution_time:.2f}s")
            if not result.passed and result.error_message:
                print(f"    Error: {result.error_message}")
        
        # Calculate summary
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = len(results) - passed_tests
        
        # Category breakdown
        category_stats = {}
        for result in results:
            category = result.test_case.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0, "failed": 0}
            category_stats[category]["total"] += 1
            if result.passed:
                category_stats[category]["passed"] += 1
            else:
                category_stats[category]["failed"] += 1
        
        report = TestReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(test_cases),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            results=results,
            summary={
                "pass_rate": (passed_tests / len(test_cases) * 100) if test_cases else 0,
                "category_stats": category_stats,
                "average_execution_time": sum(r.execution_time for r in results) / len(results) if results else 0
            }
        )
        
        return report
    
    def generate_report(self, report: TestReport, output_file: Optional[str] = None):
        """Generate a detailed test report"""
        if output_file is None:
            output_file = f"agent_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = Path("backend/tests/reports") / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        report_dict = {
            "timestamp": report.timestamp,
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "summary": report.summary,
            "results": [
                {
                    "test_name": r.test_case.name,
                    "category": r.test_case.category,
                    "description": r.test_case.description,
                    "message": r.test_case.message,
                    "passed": r.passed,
                    "response_status": r.response_status,
                    "execution_time": r.execution_time,
                    "expected": {
                        "intent": r.test_case.expected_intent,
                        "web_search": r.test_case.expected_web_search,
                        "should_edit": r.test_case.expected_should_edit,
                        "should_create": r.test_case.expected_should_create,
                    },
                    "actual": {
                        "intent": r.actual_intent,
                        "web_search": r.actual_web_search,
                        "should_edit": r.actual_should_edit,
                        "should_create": r.actual_should_create,
                    },
                    "error_message": r.error_message,
                    "response_preview": r.response_content,
                }
                for r in report.results
            ]
        }
        
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        # Also generate a human-readable summary
        summary_path = output_path.with_suffix(".txt")
        with open(summary_path, "w") as f:
            f.write("="*80 + "\n")
            f.write("AGENT EDGE CASE TEST REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Timestamp: {report.timestamp}\n")
            f.write(f"Total Tests: {report.total_tests}\n")
            f.write(f"Passed: {report.passed_tests} ({report.summary['pass_rate']:.1f}%)\n")
            f.write(f"Failed: {report.failed_tests}\n")
            f.write(f"Average Execution Time: {report.summary['average_execution_time']:.2f}s\n\n")
            
            f.write("Category Breakdown:\n")
            f.write("-"*80 + "\n")
            for category, stats in report.summary["category_stats"].items():
                pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                f.write(f"{category:30s} {stats['passed']}/{stats['total']} passed ({pass_rate:.1f}%)\n")
            f.write("\n")
            
            f.write("Failed Tests:\n")
            f.write("-"*80 + "\n")
            failed_results = [r for r in report.results if not r.passed]
            if failed_results:
                for result in failed_results:
                    f.write(f"\n✗ {result.test_case.name}\n")
                    f.write(f"  Category: {result.test_case.category}\n")
                    f.write(f"  Message: {result.test_case.message}\n")
                    f.write(f"  Status: {result.response_status}\n")
                    if result.error_message:
                        f.write(f"  Error: {result.error_message}\n")
                    if result.response_content:
                        f.write(f"  Response Preview: {result.response_content[:200]}...\n")
            else:
                f.write("No failed tests! 🎉\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("All Test Results:\n")
            f.write("="*80 + "\n\n")
            for result in report.results:
                status_icon = "✓" if result.passed else "✗"
                f.write(f"{status_icon} {result.test_case.name}\n")
                f.write(f"   Category: {result.test_case.category}\n")
                f.write(f"   Execution Time: {result.execution_time:.2f}s\n")
                if not result.passed:
                    f.write(f"   Error: {result.error_message}\n")
                f.write("\n")
        
        print(f"\n{'='*80}")
        print(f"Test Report Generated:")
        print(f"  JSON: {output_path}")
        print(f"  Summary: {summary_path}")
        print(f"{'='*80}\n")
        
        return output_path, summary_path


# Pytest fixtures and tests
@pytest.fixture
def auth_token(client):
    """Get authentication token"""
    client.post(
        "/api/auth/register",
        json={"email": "test_agent@example.com", "password": "testpassword123"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test_agent@example.com", "password": "testpassword123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def project_id(client, auth_token):
    """Create a test project"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/projects",
        json={"name": "Agent Test Project", "description": "Test project"},
        headers=headers
    )
    return response.json()["id"]


def test_agent_edge_cases(client, auth_token, project_id):
    """Run all agent edge case tests"""
    tester = AgentTester(client, auth_token, project_id)
    report = tester.run_all_tests()
    tester.generate_report(report)
    
    # Assert overall pass rate (adjust threshold as needed)
    pass_rate = report.summary["pass_rate"]
    assert pass_rate >= 70.0, f"Pass rate {pass_rate:.1f}% is below threshold of 70%"


# Standalone execution
if __name__ == "__main__":
    import sys
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    # Add backend directory to Python path for standalone execution
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    from app.core.database import Base, get_db
    from app.main import app
    # Import TestClient after sys.path is set up to ensure correct version
    from fastapi.testclient import TestClient
    
    # Create test database (replicating conftest.py logic)
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create database session
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    # Create test client with dependency override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create a synchronous wrapper around httpx.AsyncClient to work with ASGITransport
    # This avoids the TestClient version compatibility issues
    import httpx
    import asyncio
    from httpx import ASGITransport
    
    class SyncTestClient:
        """Synchronous wrapper around httpx.AsyncClient for testing"""
        def __init__(self, app):
            self.app = app
            self.transport = ASGITransport(app=app)
            self.base_url = "http://testserver"
        
        def _run_async(self, coro):
            """Run async coroutine in event loop"""
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        
        def post(self, url, **kwargs):
            async def _post():
                async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                    return await client.post(url, **kwargs)
            return self._run_async(_post())
        
        def get(self, url, **kwargs):
            async def _get():
                async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                    return await client.get(url, **kwargs)
            return self._run_async(_get())
        
        def put(self, url, **kwargs):
            async def _put():
                async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                    return await client.put(url, **kwargs)
            return self._run_async(_put())
        
        def delete(self, url, **kwargs):
            async def _delete():
                async with httpx.AsyncClient(transport=self.transport, base_url=self.base_url) as client:
                    return await client.delete(url, **kwargs)
            return self._run_async(_delete())
    
    client_instance = SyncTestClient(app)
    
    try:
        # Get auth token
        client_instance.post(
            "/api/auth/register",
            json={"email": "test_agent@example.com", "password": "testpassword123"}
        )
        response = client_instance.post(
            "/api/auth/login",
            json={"email": "test_agent@example.com", "password": "testpassword123"}
        )
        token = response.json()["access_token"]
        
        # Create project
        headers = {"Authorization": f"Bearer {token}"}
        project_response = client_instance.post(
            "/api/projects",
            json={"name": "Agent Test Project", "description": "Test project"},
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        # Run tests
        tester = AgentTester(client_instance, token, project_id)
        report = tester.run_all_tests()
        tester.generate_report(report)
    
        # Print summary
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests} ({report.summary['pass_rate']:.1f}%)")
        print(f"Failed: {report.failed_tests}")
        print(f"{'='*80}\n")
    finally:
        # Cleanup
        db_session.close()
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()

