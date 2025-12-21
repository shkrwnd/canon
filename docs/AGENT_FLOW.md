# Agent Flow Documentation

This document explains the complete flow of how the agent processes user requests, from API endpoint to response.

## Overview

When a user sends a message to the agent, the system goes through multiple stages:
1. API endpoint receives request
2. Chat management (get/create chat, store messages)
3. Agent decision making (LLM analyzes intent)
4. Action execution (edit/create documents, web search)
5. Response formatting
6. Response storage and return

---

## Step-by-Step Flow

### Step 1: API Endpoint Receives Request

**File:** `backend/app/api/routes/agent.py`

**Endpoint:** `POST /api/agent/act`

**Request Schema:**
```json
{
  "message": "Add my favorite recipes",
  "project_id": 1,
  "document_id": null,  // optional
  "chat_id": null       // optional
}
```

**What Happens:**
1. FastAPI receives the POST request
2. `get_current_user` dependency validates JWT token and extracts user
3. `get_agent_service` dependency injects `AgentService` with:
   - Database session
   - LLMService (singleton)
   - DocumentService
4. `get_chat_service` dependency injects `ChatService`
5. Calls `agent_service.process_agent_action_with_chat()`

**Code Location:**
```python
@router.post("/act", response_model=AgentActionResponse)
async def agent_action(
    request: AgentActionRequest,
    current_user: User = Depends(get_current_user),
    agent_service: AgentService = Depends(get_agent_service),
    chat_service: ChatService = Depends(get_chat_service)
):
    return await agent_service.process_agent_action_with_chat(
        user_id=current_user.id,
        request=request,
        chat_service=chat_service
    )
```

---

### Step 2: Chat Management

**File:** `backend/app/services/agent_service.py` (lines 328-424)

#### 2a. Get or Create Chat

**Logic:**
- If `chat_id` is provided:
  - Try to retrieve existing chat
  - If chat exists but belongs to different project → Create new chat
  - If chat doesn't exist → Create new chat
- If no `chat_id`:
  - Create new chat for the `project_id`
  - `project_id` is required for new chats

**Code:**
```python
if request.chat_id:
    chat = chat_service.get_chat(user_id, request.chat_id)
    if chat.project_id != request.project_id:
        # Mismatch - create new chat
        chat = None

if not chat:
    chat = chat_service.create_chat(
        user_id,
        ChatCreate(project_id=request.project_id)
    )
```

#### 2b. Store User Message

**What Happens:**
- Creates a `ChatMessage` record with:
  - `role`: `USER`
  - `content`: User's message
  - `metadata`: Empty dict
- Saves to database

**Code:**
```python
user_message = chat_service.add_message(
    user_id,
    chat.id,
    ChatMessageCreate(
        role=MessageRole.USER,
        content=request.message,
        metadata={}
    )
)
```

#### 2c. Get Chat History

**What Happens:**
- Retrieves all messages from the chat (excluding the one just added)
- Formats as list of dicts: `[{"role": "user/assistant", "content": "..."}]`
- Limits to last 10 messages for context
- Ensures roles are strings (handles enum values)

**Code:**
```python
chat_messages_db = chat_service.get_chat_messages(user_id, chat.id)
chat_history_for_llm = [
    {"role": msg.role.value if hasattr(msg.role, 'value') else msg.role, 
     "content": msg.content}
    for msg in chat_messages_db[:-1]  # Exclude last (just added)
]
```

---

### Step 3: Process Agent Action

**File:** `backend/app/services/agent_service.py` (lines 39-326)

This is the core agent logic that makes decisions and executes actions.

#### 3a. Load Project Context

**What Happens:**
1. Get project by `project_id` and `user_id`
2. Get all documents in the project
3. Build `documents_list` with:
   - `id`: Document ID
   - `name`: Document name
   - `standing_instruction`: Document's standing instruction
   - `content`: Full document content (or truncated for large docs)

**Code:**
```python
project = self.project_repo.get_by_user_and_id(user_id, project_id)
project_documents = self.document_repo.get_by_project_id(project_id)
documents_list = [
    {
        "id": d.id,
        "name": d.name,
        "standing_instruction": d.standing_instruction,
        "content": d.content
    }
    for d in project_documents
]
```

#### 3b. Get LLM Decision

**File:** `backend/app/services/llm_service.py` (lines 39-122)

**What Happens:**

1. **Generate Prompt** (`PromptService.get_agent_decision_prompt`):
   - Includes user message
   - Includes all documents with content (smart truncation for large docs)
   - Includes project context (id, name, description)
   - Includes chat history (last 10 messages)
   - Includes detailed instructions for:
     - Intent detection (conversation vs edit vs create)
     - Document resolution (which document to edit/create)
     - Web search criteria (when to search)
     - Response formatting (JSON schema)

2. **Build Messages Array**:
   ```python
   messages = [
       {
           "role": "system",
           "content": "You are a helpful assistant..."
       },
       # ... chat history messages (last 10)
       {
           "role": "user",
           "content": prompt
       }
   ]
   ```

3. **Call LLM Provider**:
   - Model: Default model (e.g., `gpt-4`)
   - Temperature: `0.5`
   - Response format: `JSON object`
   - Rate limiting: Semaphore for concurrent requests

4. **Parse JSON Response**:
   ```json
   {
     "should_edit": false,
     "should_create": true,
     "document_id": null,
     "document_name": "Recipes",
     "document_content": "...",
     "standing_instruction": "...",
     "needs_clarification": false,
     "pending_confirmation": false,
     "needs_web_search": false,
     "search_query": null,
     "intent_statement": "I'll create a new document called 'Recipes'",
     "reasoning": "User wants to add recipes, no existing document found",
     "conversational_response": null,
     "change_summary": null,
     "content_summary": "Created a Recipes document with sections for..."
   }
   ```

**Code:**
```python
decision = await self.llm_service.get_agent_decision(
    user_message, 
    documents_list, 
    project_context=project_context,
    chat_history=chat_history
)
```

#### 3c. Execute Decision

Based on the LLM's decision, the system executes different actions:

##### If `should_edit: true`

**What Happens:**
1. Get target document by `document_id`
2. If document exists:
   - Call `LLMService.rewrite_document_content()`
   - Prompt includes:
     - User's edit request
     - Document's standing instruction
     - Current document content
     - Web search results (if available)
   - LLM returns: Complete rewritten markdown content
   - Update document in database
   - Commit transaction

**Code:**
```python
if decision.get("should_edit") and decision.get("document_id"):
    target_document = self.document_repo.get_by_user_and_id(
        user_id, 
        decision["document_id"]
    )
    if target_document:
        new_content = await self.llm_service.rewrite_document_content(
            user_message=user_message,
            standing_instruction=target_document.standing_instruction,
            current_content=target_document.content,
            web_search_results=web_search_results
        )
        updated_document_obj = self.document_repo.update(
            decision["document_id"],
            content=new_content
        )
        self.document_repo.commit()
```

##### If `should_create: true`

**What Happens:**
1. **Extract `document_name`** (Priority order):
   - **Priority 1**: From `decision["document_name"]` (LLM provided)
   - **Priority 2**: From `intent_statement` pattern matching:
     - Look for "called X", "named X", "for X"
     - Look for "create X" pattern
   - **Priority 3**: From user message noun extraction:
     - Find action words ("add", "create", "make", "new")
     - Extract next 1-3 words as potential name
   - **Priority 4**: Fallback: `"Document {count + 1}"`

2. **Get initial content**:
   - From `decision["document_content"]` (if provided)
   - Append `web_search_results` if available

3. **Create document**:
   - Call `document_service.create_document()`
   - Handle `ValidationError` (e.g., duplicate name)
   - Store error context if creation fails

**Code:**
```python
if decision.get("should_create") and project_id:
    # Extract document_name (4-priority fallback system)
    document_name = decision.get("document_name")
    if not document_name:
        # Try intent_statement pattern matching
        # Try user message extraction
        # Fallback to generic name
    
    # Get initial content
    initial_content = decision.get("document_content") or ""
    if web_search_results:
        initial_content += f"\n\n{web_search_results}"
    
    # Create document
    try:
        created_document_obj = self.document_service.create_document(
            user_id=user_id,
            project_id=project_id,
            document_data=DocumentCreate(
                name=document_name,
                project_id=project_id,
                standing_instruction=decision.get("standing_instruction") or "",
                content=initial_content
            )
        )
    except ValidationError as ve:
        # Handle duplicate name or other validation errors
        # Store error context for user feedback
```

##### If `needs_web_search: true`

**What Happens:**
- Call `search_web(search_query)`
- Store results for document rewrite/creation
- Results are included in the document content

**Code:**
```python
if decision.get("needs_web_search") and decision.get("search_query"):
    web_search_results = search_web(decision["search_query"])
    web_search_performed = True
```

---

### Step 4: Format Agent Response

**File:** `backend/app/services/agent_service.py` (lines 435-594)

The system formats the agent's response based on the decision type and execution result.

#### 4a. Needs Clarification

**When:** `needs_clarification: true`

**Response:**
```
agent_response_content = clarification_question
```

**Example:**
```
"Which document should I add the dessert section to? 
You have: Recipes, Travel Guide, Budget"
```

#### 4b. Pending Confirmation

**When:** `pending_confirmation: true`

**Response:**
```
agent_response_content = confirmation_prompt
```

**Example:**
```
"I'll remove the Budget section from the Budget document. 
This will delete all budget information. Should I proceed?"
```

#### 4c. Document Created Successfully

**When:** `should_create: true` AND `created_document` exists

**Response Format:**
```
"I've created the document 'Recipes' in this project.

**Document Content Summary:**
[content_summary from LLM - 3-5 sentences describing what's in the document]

_I performed a web search to gather initial content._"  // if web_search_performed
```

**Code:**
```python
if should_create and result.get("created_document"):
    parts = []
    # Part 1: Action summary (past tense)
    if intent_statement:
        intent = intent_statement.replace("I'll create", "I've created")
        parts.append(intent)
    
    # Part 2: Content summary
    if content_summary:
        parts.append(f"\n\n**Document Content Summary:**\n{content_summary}")
    
    # Part 3: Web search note
    if result.get("web_search_performed"):
        parts.append("\n\n_I performed a web search to gather initial content._")
    
    agent_response_content = "\n".join(parts)
```

#### 4d. Document Creation Failed

**When:** `should_create: true` BUT `created_document` is None

**Response Format (Duplicate Name):**
```
"A document named 'Recipes' already exists in this project.
I can add this content to the existing document instead. 
Would you like me to update 'Recipes' with the new content?

Would you like me to:
1. Add this content to the existing document
2. Create a new document with a different name"
```

**Response Format (Other Errors):**
```
"I tried to create the document, but encountered an issue.
The document name wasn't specified. Please try again with a clearer request, 
like 'Create a document called Recipes'."
```

#### 4e. Document Updated Successfully

**When:** `should_edit: true` AND `updated_document` exists

**Response Format:**
```
"I'll add your favorite recipes to the Recipes document.

**Content Summary:**
[content_summary from LLM - describes what was added/changed]

_I performed a web search to ensure accuracy._"  // if web_search_performed
```

#### 4f. Conversational Response

**When:** `should_edit: false` AND `should_create: false`

**Response:**
- If `conversational_response` provided by LLM → use it
- Otherwise → Call `LLMService.generate_conversational_response()`
  - Includes chat history
  - Includes document context if user asking about content
  - Generates natural language response

**Code:**
```python
if conversational_response:
    agent_response_content = conversational_response
else:
    # Generate conversational response
    agent_response_content = await self.llm_service.generate_conversational_response(
        request.message,
        context,
        chat_history=chat_history_for_llm
    )
```

---

### Step 5: Store Agent Response

**File:** `backend/app/services/agent_service.py` (lines 595-616)

**What Happens:**
- Creates a `ChatMessage` record with:
  - `role`: `ASSISTANT`
  - `content`: Formatted agent response
  - `metadata`: Decision details for analytics

**Code:**
```python
agent_message = chat_service.add_message(
    user_id,
    chat.id,
    ChatMessageCreate(
        role=MessageRole.ASSISTANT,
        content=agent_response_content,
        metadata={
            "decision": result["decision"],
            "web_search_performed": result.get("web_search_performed", False),
            "document_updated": result.get("updated_document") is not None,
            "needs_clarification": needs_clarification,
            "pending_confirmation": pending_confirmation,
            "should_create": should_create
        }
    )
)
```

---

### Step 6: Publish Event

**File:** `backend/app/services/agent_service.py` (lines 625-642)

**What Happens:**
- Publishes `AgentActionCompletedEvent` to event bus
- Event includes:
  - `user_id`, `chat_id`, `project_id`, `document_id`
  - `action_type`: "agent_action"
  - `success`: Boolean (true if document created/updated)
  - `metadata`: Decision details

**Purpose:**
- Analytics tracking
- Monitoring
- Logging
- Cross-cutting concerns

**Code:**
```python
event_bus.publish(AgentActionCompletedEvent(
    user_id=user_id,
    chat_id=chat.id,
    project_id=request.project_id or chat.project_id,
    document_id=...,
    action_type="agent_action",
    success=result.get("updated_document") is not None or result.get("created_document") is not None,
    metadata={...}
))
```

---

### Step 7: Build and Return Response

**File:** `backend/app/services/agent_service.py` (lines 646-652)

**What Happens:**
- Converts updated/created document to `DocumentSchema` if exists
- Builds `AgentActionResponse` with:
  - `document`: `DocumentSchema` or `None`
  - `chat_message`: `ChatMessageSchema` (agent's response)
  - `agent_decision`: Full decision JSON
  - `web_search_performed`: Boolean

**Code:**
```python
updated_document_schema = None
if result.get("updated_document"):
    updated_document_schema = DocumentSchema(**result["updated_document"])
elif result.get("created_document"):
    updated_document_schema = DocumentSchema(**result["created_document"])

return AgentActionResponse(
    document=updated_document_schema,
    chat_message=ChatMessageSchema.model_validate(agent_message),
    agent_decision=result["decision"],
    web_search_performed=result.get("web_search_performed", False)
)
```

---

### Step 8: FastAPI Serializes and Returns

**File:** `backend/app/api/routes/agent.py`

**What Happens:**
- FastAPI validates response against `AgentActionResponse` schema
- Serializes to JSON
- Returns HTTP 200 with response body

**Response Schema:**
```json
{
  "document": {
    "id": 1,
    "name": "Recipes",
    "content": "...",
    "project_id": 1,
    ...
  },
  "chat_message": {
    "id": 123,
    "role": "assistant",
    "content": "I've created the document 'Recipes'...",
    ...
  },
  "agent_decision": {
    "should_edit": false,
    "should_create": true,
    ...
  },
  "web_search_performed": false
}
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. POST /api/agent/act                                      │
│    Request: {message, project_id, chat_id, document_id}   │
│    - Auth: get_current_user                                  │
│    - Dependencies: get_agent_service, get_chat_service     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. process_agent_action_with_chat()                         │
│    ├─ Get/Create Chat (by chat_id or project_id)            │
│    ├─ Store User Message (role: USER)                        │
│    └─ Get Chat History (last 10 messages)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. process_agent_action()                                    │
│    ├─ Load Project & Documents                              │
│    │   └─ Build documents_list with content                 │
│    ├─ Get LLM Decision                                      │
│    │   ├─ Generate Prompt (docs, history, context)         │
│    │   ├─ Call LLM Provider (JSON mode)                      │
│    │   └─ Parse JSON Decision                              │
│    └─ Execute Decision:                                     │
│        ├─ If should_edit → Rewrite Document                │
│        ├─ If should_create → Create Document                │
│        └─ If needs_web_search → Search Web                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Format Agent Response                                    │
│    ├─ Based on decision type (clarification/confirmation/  │
│    │  create/edit/conversation)                            │
│    ├─ Include summaries, error messages                      │
│    └─ Generate conversational response if needed           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Store Agent Message                                      │
│    └─ Save to Chat (role: ASSISTANT, with metadata)        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Publish Event                                             │
│    └─ AgentActionCompletedEvent → Event Bus                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Return AgentActionResponse                               │
│    └─ FastAPI serializes to JSON                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Two-Phase Processing

- **`process_agent_action_with_chat()`**: Handles chat orchestration, message storage, response formatting
- **`process_agent_action()`**: Core agent logic - decision making and action execution

### 2. LLM Calls

The LLM is called **up to 2 times** per request:

1. **Intent Detection** (`get_agent_decision`):
   - Purpose: Understand user intent and make decision
   - Input: User message, documents, chat history, project context
   - Output: JSON decision object

2. **Content Generation** (`rewrite_document_content` or `generate_conversational_response`):
   - Purpose: Generate actual content (document rewrite or conversational response)
   - Input: User request, document content, standing instructions, web search results
   - Output: Markdown content or natural language response

### 3. Chat History

- Last 10 messages are included in LLM prompts
- Enables understanding of follow-up questions
- Maintains conversation context
- Roles are normalized to strings ("user" or "assistant")

### 4. Error Handling

- **Document Creation Failures**: Caught and formatted into user-friendly messages
- **Invalid Document IDs**: Trigger clarification questions
- **Validation Errors**: Provide specific error messages
- **LLM Errors**: Logged and handled gracefully

### 5. Telemetry

- **OpenTelemetry Spans**: Track each operation for observability
- **Event Bus**: Publish events for analytics and monitoring
- **Structured Logging**: All operations are logged with context

---

## Example Flow: "Add my favorite recipes"

1. **User sends**: `"Add my favorite recipes"` to project_id=1

2. **System loads**:
   - Project: "My Project"
   - Documents: [] (empty)

3. **LLM Decision**:
   ```json
   {
     "should_create": true,
     "document_name": "Recipes",
     "intent_statement": "I'll create a new document called 'Recipes'",
     "content_summary": "Created a Recipes document with sections for breakfast, lunch, dinner..."
   }
   ```

4. **System executes**:
   - Extracts `document_name`: "Recipes"
   - Creates document with name "Recipes"
   - Stores initial content

5. **System responds**:
   ```
   "I've created the document 'Recipes' in this project.
   
   **Document Content Summary:**
   Created a Recipes document with sections for breakfast, lunch, dinner..."
   ```

6. **Response stored** in chat for persistence

---

## Notes

- All database operations are wrapped in transactions
- OpenTelemetry spans provide observability
- Event bus enables decoupled cross-cutting concerns
- Chat history ensures context-aware responses
- Smart content truncation for large documents (first 1500 + last 500 chars)
- Document name extraction uses 4-priority fallback system
- Error handling provides user-friendly feedback

