"""
Tool Registry - Register and execute tools.

The ToolRegistry follows the Registry pattern to manage and execute
various tools (web search, document operations, etc.) in a unified way.
"""

from typing import Dict, Any, Callable, Optional, List
from enum import Enum
from pydantic import BaseModel


class ToolName(str, Enum):
    """Available tool names."""
    WEB_SEARCH = "web.search"
    DOCS_SEARCH = "docs.search"
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_UPDATE = "document.update"
    # Future: CALENDAR_SEARCH = "calendar.search"


class ToolResult(BaseModel):
    """Result from tool execution."""
    tool: ToolName
    output_text: str
    sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None


# Type alias for tool executor functions
ToolExecutor = Callable[[Dict[str, Any]], ToolResult]


class ToolRegistry:
    """
    Registry for managing and executing tools.
    
    Follows the Registry pattern to decouple tool registration
    from tool execution.
    """
    
    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[ToolName, ToolExecutor] = {}
        self._async_tools: Dict[ToolName, Callable] = {}
    
    def register(self, name: ToolName, executor: ToolExecutor) -> None:
        """
        Register a synchronous tool executor.
        
        Args:
            name: Tool name
            executor: Function that takes Dict[str, Any] and returns ToolResult
        """
        if name in self._tools or name in self._async_tools:
            raise ValueError(f"Tool {name} is already registered")
        self._tools[name] = executor
    
    def register_async(self, name: ToolName, executor: Callable) -> None:
        """
        Register an asynchronous tool executor.
        
        Args:
            name: Tool name
            executor: Async function that takes Dict[str, Any] and returns ToolResult
        """
        if name in self._tools or name in self._async_tools:
            raise ValueError(f"Tool {name} is already registered")
        self._async_tools[name] = executor
    
    def run(self, name: ToolName, tool_input: Dict[str, Any]) -> ToolResult:
        """
        Execute a synchronous tool.
        
        Args:
            name: Tool name
            tool_input: Input parameters for the tool
        
        Returns:
            ToolResult from tool execution
        
        Raises:
            KeyError: If tool is not registered
        """
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name](tool_input)
    
    async def run_async(self, name: ToolName, tool_input: Dict[str, Any]) -> ToolResult:
        """
        Execute an asynchronous tool.
        
        Args:
            name: Tool name
            tool_input: Input parameters for the tool
        
        Returns:
            ToolResult from tool execution
        
        Raises:
            KeyError: If tool is not registered
        """
        if name not in self._async_tools:
            raise KeyError(f"Tool not registered: {name}")
        return await self._async_tools[name](tool_input)
    
    def list_tools(self) -> List[ToolName]:
        """
        List all registered tools.
        
        Returns:
            List of registered tool names
        """
        return list(self._tools.keys()) + list(self._async_tools.keys())
    
    def is_registered(self, name: ToolName) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            name: Tool name
        
        Returns:
            True if tool is registered
        """
        return name in self._tools or name in self._async_tools


# Tool executor implementations

def create_web_search_executor(web_search_service) -> Callable:
    """
    Create web search tool executor.
    
    Args:
        web_search_service: WebSearchService instance
    
    Returns:
        Async executor function
    """
    async def executor(tool_input: Dict[str, Any]) -> ToolResult:
        """
        Execute web search tool.
        
        Args:
            tool_input: Dict with 'query' and optional 'recency_days'
        
        Returns:
            ToolResult with search results
        """
        query = tool_input.get("query", "")
        if not query:
            return ToolResult(
                tool=ToolName.WEB_SEARCH,
                output_text="Error: query parameter is required",
                success=False,
                error="Missing query parameter"
            )
        
        try:
            # Perform web search
            web_search_result = await web_search_service.search_with_retry(
                initial_query=query,
                user_message=query,
                context=tool_input.get("context")
            )
            
            # Get best results
            results = web_search_result.get_best_results()
            
            # Extract sources
            sources = []
            if results:
                import re
                url_pattern = r'URL:\s*(https?://[^\s\n]+)'
                urls = re.findall(url_pattern, results)
                sources = urls
            
            return ToolResult(
                tool=ToolName.WEB_SEARCH,
                output_text=results or "No results found",
                sources=sources,
                metadata={
                    "attempts": len(web_search_result.attempts),
                    "was_retried": web_search_result.was_retried()
                },
                success=True
            )
        except Exception as e:
            return ToolResult(
                tool=ToolName.WEB_SEARCH,
                output_text=f"Error performing web search: {str(e)}",
                success=False,
                error=str(e)
            )
    
    return executor


def create_docs_search_executor(document_repo) -> Callable:
    """
    Create document search tool executor.
    
    Args:
        document_repo: DocumentRepository instance
    
    Returns:
        Executor function
    """
    def executor(tool_input: Dict[str, Any]) -> ToolResult:
        """
        Execute document search tool.
        
        Args:
            tool_input: Dict with 'query' and optional 'file_type', 'project_id'
        
        Returns:
            ToolResult with matching documents
        """
        query = tool_input.get("query", "")
        if not query:
            return ToolResult(
                tool=ToolName.DOCS_SEARCH,
                output_text="Error: query parameter is required",
                success=False,
                error="Missing query parameter"
            )
        
        try:
            project_id = tool_input.get("project_id")
            file_type = tool_input.get("file_type")
            
            # Get documents for project
            if project_id:
                documents = document_repo.get_by_project_id(project_id)
            else:
                documents = []
            
            # Simple text search (can be enhanced with vector search)
            matching_docs = []
            query_lower = query.lower()
            
            for doc in documents:
                # Search in name and content
                if (query_lower in doc.name.lower() or 
                    (doc.content and query_lower in doc.content.lower())):
                    matching_docs.append({
                        "id": doc.id,
                        "name": doc.name,
                        "summary": doc.content[:200] + "..." if doc.content and len(doc.content) > 200 else (doc.content or "")
                    })
            
            if not matching_docs:
                return ToolResult(
                    tool=ToolName.DOCS_SEARCH,
                    output_text=f"No documents found matching: {query}",
                    success=True
                )
            
            # Format results
            result_text = f"Found {len(matching_docs)} document(s) matching '{query}':\n"
            for doc in matching_docs:
                result_text += f"- {doc['name']} (id: {doc['id']}): {doc['summary']}\n"
            
            return ToolResult(
                tool=ToolName.DOCS_SEARCH,
                output_text=result_text.strip(),
                metadata={"count": len(matching_docs), "documents": matching_docs},
                success=True
            )
        except Exception as e:
            return ToolResult(
                tool=ToolName.DOCS_SEARCH,
                output_text=f"Error searching documents: {str(e)}",
                success=False,
                error=str(e)
            )
    
    return executor


def create_default_tool_registry(
    web_search_service=None,
    document_repo=None
) -> ToolRegistry:
    """
    Create a default tool registry with common tools.
    
    Args:
        web_search_service: Optional WebSearchService instance
        document_repo: Optional DocumentRepository instance
    
    Returns:
        ToolRegistry with registered tools
    """
    registry = ToolRegistry()
    
    # Register web search if service provided
    if web_search_service:
        registry.register_async(
            ToolName.WEB_SEARCH,
            create_web_search_executor(web_search_service)
        )
    
    # Register document search if repo provided
    if document_repo:
        registry.register(
            ToolName.DOCS_SEARCH,
            create_docs_search_executor(document_repo)
        )
    
    return registry


def available_tools_text() -> str:
    """
    Get text description of available tools for prompts.
    
    Returns:
        Formatted text describing available tools
    """
    return """Available tools:
- web.search: Search the public web for up-to-date info
  Input: {"query": string, "recency_days": number|null, "context": string|null}
  
- docs.search: Search the user's documents/notes
  Input: {"query": string, "file_type": "doc"|"sheet"|"slides"|null, "project_id": number|null}
  
- document.create: Create a new document
  Input: {"name": string, "content": string, "project_id": number, "standing_instruction": string|null}
  
- document.update: Update an existing document
  Input: {"document_id": number, "content": string, "edit_scope": "selective"|"full"}"""
