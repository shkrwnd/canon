"""
Agent Hard Test Cases

This file contains challenging test cases that stress-test the application's unique features:
- Two-stage prompting (intent classification + detailed decision)
- Web search with retry logic and quality evaluation
- Document validation and retry on failure
- Chat history context awareness (last 5 messages)
- Document resolution by name/content/context
- Source attribution for web search results
- Confirmation handling with context
- Multi-turn conversations
- Standing instructions
- Edit scope preservation (selective vs full)
- Full document rewrite (never appends)

Usage:
    python -m pytest backend/tests/test_agent_hard_cases.py -v
    OR
    python backend/tests/test_agent_hard_cases.py
"""

import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# Set up path for imports (needed for standalone execution)
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

import pytest
from fastapi.testclient import TestClient

# Import test infrastructure from edge cases file
from tests.test_agent_edge_cases import TestCase, TestResult, TestReport, AgentTester


class HardCaseAgentTester(AgentTester):
    """Extended tester for hard test cases with multi-turn conversation support"""
    
    def get_hard_test_cases(self) -> List[TestCase]:
        """Define hard test cases that stress-test application-specific features"""
        return [
            # ========================================================================
            # TWO-STAGE PROMPTING EDGE CASES
            # ========================================================================
            TestCase(
                name="Two-Stage: Ambiguous Intent Needs Full Context",
                message="improve the document",
                category="two_stage_prompting",
                description="Should use Stage 1 to classify as edit, then Stage 2 to resolve which document and what to improve. Tests if needs_documents flag works correctly."
            ),
            TestCase(
                name="Two-Stage: Simple Greeting Early Exit",
                message="hi",
                category="two_stage_prompting",
                expected_intent="conversation",
                expected_web_search=False,
                description="Should exit early after Stage 1 for simple greetings (token optimization)"
            ),
            TestCase(
                name="Two-Stage: Complex Edit Needs Full Documents",
                message="update all documents that mention Python to include the latest version",
                category="two_stage_prompting",
                expected_intent="edit",
                description="Should use Stage 1 to determine needs_documents=true, then Stage 2 with full document content"
            ),
            
            # ========================================================================
            # WEB SEARCH RETRY LOGIC EDGE CASES
            # ========================================================================
            TestCase(
                name="Web Search: Low Quality Results Trigger Retry",
                message="what is the current Bitcoin price",
                category="web_search_retry",
                expected_web_search=True,
                expected_intent="conversation",
                description="Should evaluate search quality and retry with different query if results are poor"
            ),
            TestCase(
                name="Web Search: Multiple Retries with Query Refinement",
                message="what are the latest AI safety regulations in 2025",
                category="web_search_retry",
                expected_web_search=True,
                expected_intent="conversation",
                description="Should retry up to max_retries with progressively refined queries"
            ),
            TestCase(
                name="Web Search: Retry Disabled Still Works",
                message="who is the current president of US",
                category="web_search_retry",
                expected_web_search=True,
                description="Should work correctly even if retry is disabled (tests retry logic doesn't break single attempt)"
            ),
            TestCase(
                name="Web Search: Quality Score Below Threshold",
                message="what are the latest React hooks best practices",
                category="web_search_retry",
                expected_web_search=True,
                description="Should retry if quality score is below min_quality_score threshold"
            ),
            
            # ========================================================================
            # DOCUMENT VALIDATION & RETRY EDGE CASES
            # ========================================================================
            TestCase(
                name="Validation: Selective Edit Loses Sections",
                message="edit the Python Guide and make the introduction more concise",
                category="document_validation",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that all original sections are preserved when making the introduction more concise. No sections should be removed or lost.",
                validation_critical=True,
                description="Should preserve all sections when doing selective edit. If validation fails, should retry with stronger preservation instructions."
            ),
            TestCase(
                name="Validation: Full Rewrite Preserves Structure",
                message="rewrite the entire Python Guide with better organization",
                category="document_validation",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that all original section headings are preserved in the rewritten document. The structure should remain intact even with better organization.",
                validation_critical=True,
                description="Should preserve all section headings even in full rewrite. Validation should catch missing sections."
            ),
            TestCase(
                name="Validation: Retry After Validation Failure",
                message="update the Python Guide to remove outdated information",
                category="document_validation",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that outdated information was removed from the document, that all current sections are preserved, and that the document remains well-structured. If validation failed initially, the retry should have succeeded in preserving structure.",
                validation_critical=True,
                description="If validation fails (sections lost), should retry once with validation_errors included in prompt"
            ),
            
            # ========================================================================
            # CHAT HISTORY CONTEXT EDGE CASES
            # ========================================================================
            TestCase(
                name="Chat History: Confirmation After 3 Messages",
                message="yes",
                category="chat_history",
                description="Should use last 5 messages to find pending confirmation from 3 messages ago"
            ),
            TestCase(
                name="Chat History: Multi-Turn Document Reference",
                message="add that to it",
                category="chat_history",
                description="Should resolve 'that' and 'it' from previous messages in chat history"
            ),
            TestCase(
                name="Chat History: Context Across 5+ Messages",
                message="update the first document we discussed",
                category="chat_history",
                description="Should use chat history to identify which document was discussed first"
            ),
            TestCase(
                name="Chat History: Decision Metadata in History",
                message="where did you save that script",
                category="chat_history",
                expected_intent="conversation",
                description="Should use decision metadata from previous messages to answer 'where' questions"
            ),
            
            # ========================================================================
            # DOCUMENT RESOLUTION COMPLEXITY
            # ========================================================================
            TestCase(
                name="Document Resolution: Similar Names (Python Guide vs Python guide)",
                message="edit the python guide",
                category="document_resolution",
                expected_should_edit=True,
                description="Should handle case-insensitive matching when multiple similar names exist"
            ),
            TestCase(
                name="Document Resolution: Content-Based Match",
                message="add hotel recommendations",
                category="document_resolution",
                expected_should_edit=True,
                description="Should match document by content (travel/itinerary doc) when name not specified"
            ),
            TestCase(
                name="Document Resolution: Context from History",
                message="add more details",
                category="document_resolution",
                description="Should use conversation history to determine which document to edit"
            ),
            TestCase(
                name="Document Resolution: Ambiguous Multiple Matches",
                message="update the guide",
                category="document_resolution",
                description="Should handle ambiguity when multiple 'guide' documents exist (may need clarification)"
            ),
            
            # ========================================================================
            # SOURCE ATTRIBUTION EDGE CASES
            # ========================================================================
            TestCase(
                name="Source Attribution: Multiple Web Search Results",
                message="edit the Python Guide and add information about the latest Python features, performance improvements, and security updates",
                category="source_attribution",
                expected_web_search=True,
                expected_should_edit=True,
                expected_contains=["## Sources"],
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains a '## Sources' section with multiple properly formatted URLs, that the document includes information about latest Python features, performance improvements, and security updates, and that all sources are relevant to these topics.",
                validation_critical=True,
                description="Should include ALL URLs from web search results in Sources section, even if multiple searches were performed"
            ),
            TestCase(
                name="Source Attribution: Retry Results Include All URLs",
                message="add the latest React performance optimizations to the Python Guide",
                category="source_attribution",
                expected_web_search=True,
                expected_should_edit=True,
                expected_contains=["## Sources"],
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains a '## Sources' section with properly formatted URLs, that the document includes information about React performance optimizations, and that all sources are relevant. If multiple search attempts were made, all relevant URLs should be included.",
                validation_critical=True,
                description="If web search was retried, should include URLs from ALL attempts in Sources section"
            ),
            TestCase(
                name="Source Attribution: Post-Processing Adds Missing Sources",
                message="edit the Python Guide and add the current Python version",
                category="source_attribution",
                expected_web_search=True,
                expected_should_edit=True,
                expected_contains=["## Sources"],
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that the document contains a '## Sources' section with properly formatted URLs, that the current Python version information is accurate and up-to-date, and that sources are relevant to Python version information.",
                validation_critical=True,
                description="If LLM forgets Sources section, post-processing should add it automatically"
            ),
            
            # ========================================================================
            # CONFIRMATION HANDLING COMPLEXITY
            # ========================================================================
            TestCase(
                name="Confirmation: Yes After Destructive Action Prompt",
                message="yes",
                category="confirmation_handling",
                description="Should check last 5 messages for pending_confirmation and execute the intended action"
            ),
            TestCase(
                name="Confirmation: No After Destructive Action Prompt",
                message="no",
                category="confirmation_handling",
                expected_intent="conversation",
                description="Should recognize 'no' as cancellation and not perform the action"
            ),
            TestCase(
                name="Confirmation: Multiple Confirmations in History",
                message="yes",
                category="confirmation_handling",
                description="Should use the most recent pending confirmation from chat history"
            ),
            
            # ========================================================================
            # MULTI-TURN CONVERSATION EDGE CASES
            # ========================================================================
            TestCase(
                name="Multi-Turn: Follow-up Question After Edit",
                message="what did you change",
                category="multi_turn",
                expected_intent="conversation",
                description="Should use chat history to understand what was changed in previous turn"
            ),
            TestCase(
                name="Multi-Turn: Reference Previous Content",
                message="add more details about that",
                category="multi_turn",
                description="Should resolve 'that' from previous agent response or user message"
            ),
            TestCase(
                name="Multi-Turn: Chain of Edits",
                message="now make it more concise",
                category="multi_turn",
                validate_document_content=True,
                validation_requirements="Verify that the document was made more concise (shorter, more direct language) while preserving all key information and maintaining clarity. The document should be more compact but still comprehensive.",
                validation_critical=False,  # Warning only - conciseness is somewhat subjective
                description="Should understand 'it' refers to the document edited in previous turn"
            ),
            TestCase(
                name="Multi-Turn: Question About Previous Action",
                message="why did you do that",
                category="multi_turn",
                expected_intent="conversation",
                description="Should explain reasoning from previous action using chat history"
            ),
            
            # ========================================================================
            # STANDING INSTRUCTIONS EDGE CASES
            # ========================================================================
            TestCase(
                name="Standing Instructions: Edit Respects Instructions",
                message="add a section about advanced topics",
                category="standing_instructions",
                expected_should_edit=True,
                validate_document_content=True,
                validation_requirements="Verify that a section about advanced topics was added and that the new content maintains consistency with the document's existing style, tone, and structure. The document should remain coherent and well-organized.",
                validation_critical=True,
                description="Should maintain consistency with document's standing instructions when editing"
            ),
            TestCase(
                name="Standing Instructions: Create With Instructions",
                message="create a technical guide",
                category="standing_instructions",
                expected_should_create=True,
                validate_document_content=True,
                validation_requirements="Verify that a technical guide document was created with appropriate technical content, proper structure (headings, sections), and that it follows technical documentation best practices. The document should be comprehensive and well-organized.",
                validation_critical=True,
                description="Should create document with appropriate standing instructions based on document type"
            ),
            
            # ========================================================================
            # EDIT SCOPE PRESERVATION EDGE CASES
            # ========================================================================
            TestCase(
                name="Edit Scope: Selective Edit Preserves All Sections",
                message="edit the Python Guide and improve the introduction section",
                category="edit_scope",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that all original sections (Features, Introduction, etc.) are preserved and only the introduction section was improved. The document should maintain its original structure with all headings intact.",
                validation_critical=True,
                description="Should preserve ALL other sections when doing selective edit. Validation should catch any lost sections."
            ),
            TestCase(
                name="Edit Scope: Full Rewrite Preserves Headings",
                message="rewrite the entire Python Guide with better structure",
                category="edit_scope",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that all original section headings (like 'Features', 'Introduction', etc.) are preserved even in a full rewrite. The document structure should remain intact.",
                validation_critical=True,
                description="Even in full rewrite, should preserve all section headings and structure"
            ),
            TestCase(
                name="Edit Scope: Selective After Failed Full",
                message="completely rewrite the Python Guide",
                category="edit_scope",
                expected_should_edit=True,
                requires_document="Python Guide",
                description="If full rewrite fails validation, retry should use selective scope to preserve content"
            ),
            
            # ========================================================================
            # WEB SEARCH QUALITY EVALUATION
            # ========================================================================
            TestCase(
                name="Web Search Quality: Evaluate Relevance",
                message="what are the latest TypeScript features",
                category="web_search_quality",
                expected_web_search=True,
                description="Should evaluate if search results are relevant to the query and retry if quality is low"
            ),
            TestCase(
                name="Web Search Quality: Summarize Results",
                message="what are the current best practices for React state management",
                category="web_search_quality",
                expected_web_search=True,
                description="Should summarize web search results if summarization is enabled"
            ),
            
            # ========================================================================
            # COMPLEX INTENT RESOLUTION
            # ========================================================================
            TestCase(
                name="Complex Intent: Edit + Web Search + Source Attribution",
                message="edit the document about latest Python features, make it more comprehensive, and ensure all information is current",
                category="complex_intent",
                expected_web_search=True,
                expected_should_edit=True,
                expected_contains=["## Sources"],
                requires_document="Latest Python Features",
                validate_document_content=True,
                validation_requirements="Verify that the document is comprehensive (covers multiple aspects of latest Python features), contains current and up-to-date information, includes a '## Sources' section with relevant URLs, and maintains good structure and organization.",
                validation_critical=True,
                description="Combines edit intent, web search trigger, and source attribution - tests full flow"
            ),
            TestCase(
                name="Complex Intent: Create + Web Search + Content Generation",
                message="create a comprehensive guide about the latest AI developments in 2025",
                category="complex_intent",
                expected_web_search=True,
                expected_should_create=True,
                expected_contains=["## Sources"],
                validate_document_content=True,
                validation_requirements="Verify that a comprehensive guide about latest AI developments in 2025 was created, that it contains current and accurate information about AI developments, includes a '## Sources' section with relevant URLs, and has proper structure with headings and well-organized content.",
                validation_critical=True,
                description="Combines create intent, web search, content generation, and source attribution"
            ),
            TestCase(
                name="Complex Intent: Multi-Step Implicit Request",
                message="update the Python Guide with the latest version and also create a quick reference card",
                category="complex_intent",
                description="Tests if agent can handle implicit multi-step requests (may need clarification or do sequentially)"
            ),
            
            # ========================================================================
            # ERROR RECOVERY & RESILIENCE
            # ========================================================================
            TestCase(
                name="Error Recovery: Document Not Found Graceful Handling",
                message="edit the document called DefinitelyDoesNotExist12345",
                category="error_recovery",
                expected_should_edit=True,
                description="Should recognize edit intent even if document doesn't exist, provide helpful error message"
            ),
            TestCase(
                name="Error Recovery: Validation Failure Retry",
                message="rewrite the Python Guide completely",
                category="error_recovery",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that even after a complete rewrite, all original section headings are preserved, the document maintains its structure, and the content is well-organized. If validation failed initially, the retry should have succeeded.",
                validation_critical=True,
                description="If validation fails (sections lost), should retry with validation errors and succeed on retry"
            ),
            TestCase(
                name="Error Recovery: Web Search Failure",
                message="what is the current price of a non-existent cryptocurrency XYZ123",
                category="error_recovery",
                expected_web_search=True,
                description="Should handle web search failures gracefully and still provide response"
            ),
            
            # ========================================================================
            # PERFORMANCE & EFFICIENCY EDGE CASES
            # ========================================================================
            TestCase(
                name="Performance: Large Document Edit",
                message="edit the Python Guide and add a comprehensive FAQ section",
                category="performance",
                expected_should_edit=True,
                requires_document="Python Guide",
                validate_document_content=True,
                validation_requirements="Verify that a comprehensive FAQ section was added to the document, that it contains relevant questions and answers about Python, that all original sections are preserved, and that the document remains well-structured.",
                validation_critical=True,
                description="Should handle editing large documents efficiently (tests document truncation logic)"
            ),
            TestCase(
                name="Performance: Multiple Documents Context",
                message="which document has the most content about Python",
                category="performance",
                expected_intent="conversation",
                description="Should efficiently analyze multiple documents without loading full content unnecessarily"
            ),
            
            # ========================================================================
            # BOUNDARY CONDITIONS
            # ========================================================================
            TestCase(
                name="Boundary: Exactly 5 Messages in History",
                message="what did you do 5 messages ago",
                category="boundary_conditions",
                expected_intent="conversation",
                description="Should correctly use last 5 messages (boundary of history length)"
            ),
            TestCase(
                name="Boundary: Empty Document Edit",
                message="edit the Python Guide",
                category="boundary_conditions",
                expected_should_edit=True,
                description="Should handle editing documents with minimal or empty content"
            ),
            TestCase(
                name="Boundary: Maximum Web Search Retries",
                message="what are the latest developments in quantum computing error correction",
                category="boundary_conditions",
                expected_web_search=True,
                description="Should respect max_retries limit and not exceed it even if quality is still low"
            ),
            
            # ========================================================================
            # REAL-WORLD SCENARIOS
            # ========================================================================
            TestCase(
                name="Real-World: Writer Workflow - Iterative Refinement",
                message="make the introduction more engaging",
                category="real_world",
                validate_document_content=True,
                validation_requirements="Verify that the introduction section was made more engaging (more compelling, interesting, or attention-grabbing) while maintaining accuracy and preserving all other sections of the document.",
                validation_critical=False,  # Warning only - engagement is somewhat subjective
                description="Simulates real writer workflow: iterative refinement of document sections"
            ),
            TestCase(
                name="Real-World: Researcher - Fact Verification",
                message="update the research document with the latest findings from December 2024",
                category="real_world",
                expected_web_search=True,
                validate_document_content=True,
                validation_requirements="Verify that the document contains information about latest findings from December 2024, that the information is current and accurate, and that it's well-integrated into the document structure. All original sections should be preserved.",
                validation_critical=True,
                description="Simulates researcher workflow: fact-checking and updating with latest information"
            ),
            TestCase(
                name="Real-World: Editor - Multi-Document Coordination",
                message="ensure all documents use consistent terminology",
                category="real_world",
                validate_document_content=True,
                validation_requirements="Check that all documents use consistent terminology for the same concepts (e.g., 'Python' not 'python' or 'PYTHON', same technical terms throughout). This is a warning-level check.",
                validation_critical=False,
                description="Simulates editor workflow: maintaining consistency across multiple documents (may need clarification)"
            ),
            TestCase(
                name="Real-World: Power User - Complex Multi-Step",
                message="create a guide about the latest Python features, make it comprehensive, include examples, and add source links",
                category="real_world",
                expected_web_search=True,
                expected_should_create=True,
                expected_contains=["## Sources"],
                validate_document_content=True,
                validation_requirements="Verify that a comprehensive guide about latest Python features was created, that it includes code examples, contains a '## Sources' section with relevant URLs, covers multiple aspects of Python features comprehensively, and has proper structure with headings and well-organized content.",
                validation_critical=True,
                description="Simulates power user: complex request with multiple requirements"
            ),
        ]
    
    def run_hard_tests(self) -> TestReport:
        """Run all hard test cases"""
        # Setup test environment first
        self.setup_test_environment()
        
        test_cases = self.get_hard_test_cases()
        results = []
        
        print(f"\n{'='*80}")
        print(f"Running {len(test_cases)} HARD test cases...")
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


# Pytest fixtures and tests
@pytest.fixture
def auth_token(client):
    """Get authentication token"""
    client.post(
        "/api/auth/register",
        json={"email": "test_hard_cases@example.com", "password": "testpassword123"}
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "test_hard_cases@example.com", "password": "testpassword123"}
    )
    return response.json()["access_token"]


@pytest.fixture
def project_id(client, auth_token):
    """Create a test project"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/api/projects",
        json={"name": "Hard Test Cases Project", "description": "Test project for hard cases"},
        headers=headers
    )
    return response.json()["id"]


def test_agent_hard_cases(client, auth_token, project_id):
    """Run all hard test cases"""
    tester = HardCaseAgentTester(client, auth_token, project_id)
    report = tester.run_hard_tests()
    tester.generate_report(report, output_file=f"agent_hard_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    # Assert overall pass rate (harder threshold for hard cases)
    pass_rate = report.summary["pass_rate"]
    assert pass_rate >= 60.0, f"Pass rate {pass_rate:.1f}% is below threshold of 60% for hard cases"


# Standalone execution
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import httpx
    
    from app.core.database import Base, get_db
    from app.main import app
    
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
            json={"email": "test_hard_cases@example.com", "password": "testpassword123"}
        )
        response = client_instance.post(
            "/api/auth/login",
            json={"email": "test_hard_cases@example.com", "password": "testpassword123"}
        )
        token = response.json()["access_token"]
        
        # Create project
        headers = {"Authorization": f"Bearer {token}"}
        project_response = client_instance.post(
            "/api/projects",
            json={"name": "Hard Test Cases Project", "description": "Test project"},
            headers=headers
        )
        project_id = project_response.json()["id"]
        
        # Run tests
        tester = HardCaseAgentTester(client_instance, token, project_id)
        report = tester.run_hard_tests()
        tester.generate_report(report, output_file=f"agent_hard_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"HARD TEST CASES SUMMARY")
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

