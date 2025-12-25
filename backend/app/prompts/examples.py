"""
Prompt examples for all intent types.
This file contains few-shot examples for the LLM to learn from.
"""

PROMPT_EXAMPLES = """
=== 1. CONVERSATION INTENT (should_edit: false, should_create: false) ===

User: "Hi!" or "hey" or "hello"
→ should_edit: false, should_create: false, needs_clarification: false, pending_confirmation: false,
  conversational_response: "Hi! How can I help with your [Project Name] project? This project contains [summary based on documents - e.g., 'information about mental health and its benefits']. Here are the documents in this project:
1. [Document Name] - [description based on content, e.g., 'contains steps to improve health']
2. [Document Name] - [description based on content, e.g., 'your daily diet routine till Friday']
What would you like to work on?"

User: "What should I add to make it better?"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "Based on your content, you might consider adding [suggestions based on document content]. For example, [specific recommendations]. Would you like me to add any of these?"

User: "Summarize the itinerary document"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "Here's a summary of your Itinerary document: [actual summary from content, including key sections, dates, locations, etc.]"

User: "Tell me about the recipes document"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "The Recipes document contains [description based on content]. It includes sections on [list sections]. [Brief overview of content]."

User: "where did you make the changes" or "where did you save it" or "where is the script"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "I [created/updated] the [Document Name] document. [Brief description of what was done]. You can find it in your project documents."
  CRITICAL: This is a QUESTION asking for location/info, NOT an action request

User: "How many documents do I have?"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "You have [number] documents in this project: [list document names]. [Brief description of each]"

User: "who is the current president of US" or "what is the capital of France"
→ should_edit: false, should_create: false, needs_clarification: false,
  needs_web_search: true, search_query: "current president of US" or "capital of France",
  conversational_response: "[Answer based on web search results - e.g., 'The current president of the United States is [name]' or 'The capital of France is Paris']"
  CRITICAL: This is a pure general knowledge question with NO document mentioned - it's conversation, not an action

User: "What's in this project?"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "This project contains [summary]. Here are the documents: [numbered list with descriptions]. What would you like to know more about?"

User: "Can you help me organize my documents?"
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "I'd be happy to help! Your project currently has [number] documents: [list]. I can help you [suggestions like: merge related documents, rename documents, add structure, etc.]. What would you like to do?"

User: "What else can you do?" or "What can you do?" or "other than what you told"
→ **First: Analyze all documents - understand project purpose, content, gaps, and opportunities**
→ **CRITICAL: DO NOT repeat the greeting format - this is a capability question requiring deep analysis**
→ should_edit: false, should_create: false, needs_clarification: false,
  conversational_response: "Based on my analysis of your [Project Name] project, here's what I can help you with:

**Current Project State:**
- [Document 1]: [Analysis - what's there, what's complete, what might be missing]
- [Document 2]: [Analysis]
- [Document 3]: [Analysis]

**Specific Suggestions Based on Your Project:**
- [Specific suggestion based on actual gaps - e.g., 'Your Itinerary has dates but no hotel bookings - I can add hotel recommendations']
- [Another specific suggestion based on content analysis - e.g., 'Your Recipes document is missing dessert recipes - I can add a desserts section']
- [Suggestion based on incomplete sections or missing related topics]

**General Capabilities:**
- Add, update, or modify content in your documents
- Create new documents for related topics
- Search the web for current information when needed
- Summarize or analyze your documents
- Maintain consistency across your project

What would you like me to work on first?"

=== 2. EDIT_REQUEST INTENT (should_edit: true) ===

User: "Add hotel recommendations to the itinerary"
→ should_edit: true, should_create: false, document_id: <itinerary_id>, edit_scope: "selective",
  intent_statement: "I'll add hotel recommendations to the Itinerary document",
  change_summary: "Adding hotel recommendations with prices",
  content_summary: "Added a new 'Hotels' section with three recommendations: The Grand Plaza (downtown, $150/night, 4-star), Seaside Resort (beachfront, $200/night, 5-star), and Budget Inn (near airport, $80/night, 3-star). Each entry includes location, price range, star rating, and key amenities like WiFi, breakfast, and parking availability."

User: "Edit the Python guide document and add the latest Python version information"
→ should_edit: true, should_create: false, document_id: <python_guide_id>, edit_scope: "selective",
  needs_web_search: true, search_query: "latest Python version 2024",
  intent_statement: "I'll add the latest Python version information to the Python guide document",
  change_summary: "Adding latest Python version information",
  content_summary: "Added a new section about the latest Python version, including version number, release date, and key new features based on current information from web search. Sources section included with all reference URLs."

User: "Add the current React best practices to the React guide"
→ should_edit: true, should_create: false, document_id: <react_guide_id>, edit_scope: "selective",
  needs_web_search: true, search_query: "React best practices 2024",
  intent_statement: "I'll add current React best practices to the React guide document",
  change_summary: "Adding current React best practices",
  content_summary: "Added a section on current React best practices for 2024, including modern patterns, hooks usage, and performance optimization techniques based on latest industry standards. Sources section included with all reference URLs."

User: "edit the document about the latest Python features to be more verbose"
→ should_edit: true, should_create: false, document_id: <latest_python_features_id>, edit_scope: "selective",
  needs_web_search: true, search_query: "latest Python features 2024",
  intent_statement: "I'll expand the document about latest Python features with more detailed information",
  change_summary: "Expanding document with more verbose descriptions of latest Python features",
  content_summary: "Expanded the document with more detailed explanations of the latest Python features, including comprehensive descriptions, use cases, and examples. All information verified with current web search results. Sources section included with all reference URLs."

User: "Add hotels"
→ **First: Analyze project - is this travel-related? Check documents for travel/itinerary content**
→ **Second: Infer intent - user likely wants hotels in travel document based on project context**
→ should_edit: true, should_create: false, document_id: <travel_document_id>, edit_scope: "selective",
  intent_statement: "I'll add hotel recommendations to your [Travel/Itinerary] document",
  change_summary: "Adding hotel recommendations",
  content_summary: "Added hotel recommendations section with [details based on project context]"

User: "Update the budget section with new numbers"
→ should_edit: true, should_create: false, document_id: <budget_document_id>, edit_scope: "selective",
  intent_statement: "I'll update the budget section with new numbers",
  change_summary: "Updating budget section with new financial figures",
  content_summary: "Updated the budget section with revised numbers: [specific changes made]"

User: "Change the title to 'My Travel Plans'"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "selective",
  intent_statement: "I'll change the title to 'My Travel Plans'",
  change_summary: "Changing document title",
  content_summary: "Updated the document title from '[old title]' to 'My Travel Plans'"

User: "Replace the heading with Version"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "selective",
  intent_statement: "I'll replace the heading with 'Version'",
  change_summary: "Replacing heading",
  content_summary: "Updated the main heading from '[old heading]' to 'Version'"
  - edit_scope: "selective" because only heading changes, all sections must be preserved

User: "Insert a new section about safety tips after the introduction"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "selective",
  intent_statement: "I'll insert a new section about safety tips after the introduction",
  change_summary: "Adding safety tips section",
  content_summary: "Added a new 'Safety Tips' section after the introduction, covering [topics covered]"

User: "Modify the conclusion paragraph to be more positive"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "selective",
  intent_statement: "I'll modify the conclusion paragraph to be more positive",
  change_summary: "Updating conclusion tone",
  content_summary: "Revised the conclusion paragraph to have a more positive tone, emphasizing [key points]"

User: "Add my favorite recipes"
→ **First check: Does a document named "Recipes" exist in PROJECT DOCUMENTS?**
  - If YES → should_edit: true, should_create: false, document_id: <recipes_document_id>, edit_scope: "selective",
    intent_statement: "I'll add your favorite recipes to the existing Recipes document",
    change_summary: "Adding favorite recipes",
    content_summary: "Added your favorite recipes: [list recipes added with brief descriptions]"
  - If NO → should_create: true, document_name: "Recipes", intent_statement: "I'll create a new document called 'Recipes' for your favorite recipes"

User: "save it" or "save that" or "save this"
→ **CRITICAL: Check conversation history for content to save**
→ should_edit: true, should_create: false, edit_scope: "selective",
  - If document mentioned in conversation → use that document_id
  - If no document mentioned → use most recent/relevant document or create new one
  - Extract content from previous agent response in conversation history
  - intent_statement: "I'll save that content to [document name]",
  - change_summary: "Saving content to document",
  - content_summary: "Saved the [content type] to [document name]: [brief description of what was saved]"
  - Example: User says "save it" after agent provided a script → should_edit: true, add script content to document

User: "rewrite the entire document"
→ should_edit: true, document_id: <document_id>, edit_scope: "full", intent_statement: "I'll rewrite the entire document"
  - edit_scope: "full" because user explicitly requested full rewrite

=== 3. CREATE_REQUEST INTENT (should_create: true) ===

User: "Create a new document for recipes"
→ **First check: Does a document named "Recipes" exist in PROJECT DOCUMENTS?**
  - If YES → should_edit: true, document_id: <recipes_document_id>, intent_statement: "I'll update the existing Recipes document"
  - If NO → should_create: true, should_edit: false, document_name: "Recipes",
    intent_statement: "I'll create a new document called 'Recipes' in this project",
    change_summary: "Creating new Recipes document",
    content_summary: "Created a new Recipes document with [initial content description]"

User: "Create a travel guide document"
→ **First check: Does a document named "Travel Guide" exist in PROJECT DOCUMENTS?**
  - If YES → should_edit: true, document_id: <travel_guide_document_id>, intent_statement: "I'll update the existing Travel Guide document"
  - If NO → should_create: true, should_edit: false, document_name: "Travel Guide",
    intent_statement: "I'll create a new document called 'Travel Guide' in this project",
    change_summary: "Creating new Travel Guide document",
    content_summary: "Created a new Travel Guide document with sections on [topics covered]"

User: "Make a new document for meeting notes"
→ **First check: Does a document named "Meeting Notes" exist in PROJECT DOCUMENTS?**
  - If NO → should_create: true, should_edit: false, document_name: "Meeting Notes",
    intent_statement: "I'll create a new document called 'Meeting Notes' for your meeting notes",
    change_summary: "Creating new Meeting Notes document",
    content_summary: "Created a new Meeting Notes document with a template structure for [purpose]"

User: "Start a new document called Budget Tracker"
→ **First check: Does a document named "Budget Tracker" exist in PROJECT DOCUMENTS?**
  - If NO → should_create: true, should_edit: false, document_name: "Budget Tracker",
    intent_statement: "I'll create a new document called 'Budget Tracker'",
    change_summary: "Creating new Budget Tracker document",
    content_summary: "Created a new Budget Tracker document with [initial structure/content]"

User: "I need a new document for my workout routine"
→ **First check: Does a document with "workout" or "routine" in the name exist?**
  - If NO → should_create: true, should_edit: false, document_name: "Workout Routine",
    intent_statement: "I'll create a new document called 'Workout Routine' for your workout plans",
    change_summary: "Creating new Workout Routine document",
    content_summary: "Created a new Workout Routine document with [initial content]"

User: "create a script" or "create a script for that" or "can you create a script"
→ **First check: Does a document named "Script" or "Video Script" exist?**
  - If NO → should_create: true, should_edit: false, document_name: "Script" or "Video Script",
    document_content: "[Generate the actual script content based on context/conversation history]",
    intent_statement: "I'll create a new document called 'Script' with the script content",
    change_summary: "Creating new Script document",
    content_summary: "Created a new Script document with [description of script content - e.g., 'a video script outline with introduction, key recommendations, engagement prompts, and conclusion']"
  - If YES → should_edit: true, document_id: <script_document_id>, intent_statement: "I'll update the existing Script document"

User: "create a plan" or "create a video script" or "create a [noun]"
→ **Pattern: "create a [noun]" → document_name: capitalize the noun**
  - "create a plan" → document_name: "Plan"
  - "create a video script" → document_name: "Video Script"
  - "create a budget" → document_name: "Budget"
  - Check if document exists first → if yes, edit instead of create

=== 4. NEEDS_CLARIFICATION INTENT (needs_clarification: true) ===

User: "Add a dessert section"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "Which document should I add the dessert section to? You have: [list all documents with brief descriptions]. Please specify the document name."

User: "Make it better"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "I'd be happy to help improve your documents! Could you clarify what you'd like me to improve? For example: [specific suggestions based on document content]. Which document are you referring to, and what specifically should be changed?"

User: "Update that"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "Which document would you like me to update? You have: [list documents]. Also, what specifically should I update?"

User: "Add more content"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "I can add more content! Which document should I add it to? You have: [list documents]. Also, what kind of content would you like me to add?"

User: "Fix the errors"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "I can help fix errors! Which document contains the errors? You have: [list documents]. What kind of errors should I look for? (e.g., typos, broken links, formatting issues)"

User: "Change something"
→ should_edit: false, should_create: false, needs_clarification: true,
  clarification_question: "What would you like me to change? Please specify: (1) Which document? You have: [list documents]. (2) What should be changed? (3) What should it be changed to?"

=== 5. NEEDS_CONFIRMATION INTENT (pending_confirmation: true) ===

User: "Delete the budget section"
→ should_edit: true, should_create: false, document_id: <budget_document_id>, edit_scope: "selective", pending_confirmation: true,
  intent_statement: "I'll remove the Budget section from the Budget document",
  confirmation_prompt: "I'll remove the Budget section from the Budget document. This will delete all budget information including [list what will be deleted]. Should I proceed?",
  change_summary: "Removing budget section"

User: "Remove the dessert section from the recipes document"
→ should_edit: true, should_create: false, document_id: <recipes_document_id>, edit_scope: "selective", pending_confirmation: true,
  intent_statement: "I'll remove the dessert section from the Recipes document",
  confirmation_prompt: "I'll remove the Dessert section from the Recipes document. This will delete all dessert recipes. Should I proceed?",
  change_summary: "Removing dessert section"

User: "Remove all content from the document"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "full", pending_confirmation: true,
  intent_statement: "I'll clear all content from the document",
  confirmation_prompt: "I'll remove all content from the [Document Name] document. This will delete everything in the document. This action cannot be undone. Should I proceed?",
  change_summary: "Clearing all document content"

User: "Clear everything and start over"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "full", pending_confirmation: true,
  intent_statement: "I'll clear the document and start fresh",
  confirmation_prompt: "I'll remove all content from the [Document Name] document and start over. This will delete everything currently in the document. Should I proceed?",
  change_summary: "Clearing document for fresh start"

User: "Remove the last 3 sections"
→ should_edit: true, should_create: false, document_id: <document_id>, edit_scope: "selective", pending_confirmation: true,
  intent_statement: "I'll remove the last 3 sections from the document",
  confirmation_prompt: "I'll remove the last 3 sections from the [Document Name] document: [list sections that will be removed]. This will permanently delete this content. Should I proceed?",
  change_summary: "Removing last 3 sections"
"""

