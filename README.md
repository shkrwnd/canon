# Canon - Living Documents Editor

An agentic editor that maintains living documents. Users express intent in natural language; the system decides what to edit, when to edit, and when to search the web.

## Features

- **Intent-driven editing**: Express changes in natural language
- **Agentic rewriting**: AI agent rewrites entire module state (never appends)
- **Web search integration**: Automatic web search when needed for factual accuracy
- **Module system**: Named, persistent documents with standing instructions
- **Chat persistence**: All conversations stored in database
- **Manual override**: Users can manually edit markdown to override agent output

## Tech Stack

### Backend
- FastAPI
- SQLite
- OpenAI GPT-4o
- Tavily (web search)
- JWT authentication

### Frontend
- React + Create React App
- TypeScript
- Tailwind CSS
- React Query
- CodeMirror (markdown editing)
- React Router

## Setup

### Backend

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file (copy from `.env.example`):
```bash
DATABASE_URL=sqlite:///./canon.db
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
JWT_SECRET_KEY=your_secret_key_here_change_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

5. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file (optional, defaults to localhost:8000):
```bash
REACT_APP_API_URL=http://localhost:8000
```

4. Start the development server:
```bash
npm start
```

The app will be available at `http://localhost:3000`

## Usage

1. **Register/Login**: Create an account or login
2. **Create Module**: Click "+ New Module" to create a document
3. **Edit via Chat**: Type natural language commands in the chat panel to edit the module
4. **Manual Edit**: Click "Edit" button to manually edit the markdown
5. **Agent Decisions**: The agent automatically decides when to edit, which module to edit, and when to search the web

## Project Structure

```
canon/
├── backend/
│   ├── app/
│   │   ├── api/routes/    # API endpoints
│   │   ├── models.py      # Database models
│   │   ├── schemas.py     # Pydantic schemas
│   │   ├── agent.py       # Agent logic
│   │   └── ...
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # Page components
│   │   ├── layouts/       # Layout components
│   │   ├── components/    # UI components
│   │   ├── services/      # Business logic
│   │   ├── clients/       # API client
│   │   ├── helpers/      # Helper functions
│   │   └── utils/        # Utilities
│   └── package.json
└── README.md
```

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/modules` - List user's modules
- `POST /api/modules` - Create module
- `GET /api/modules/{id}` - Get module
- `PUT /api/modules/{id}` - Update module (manual edit)
- `DELETE /api/modules/{id}` - Delete module
- `POST /api/agent/act` - Agent action endpoint
- `GET /api/chats` - List chats
- `POST /api/chats` - Create chat
- `GET /api/chats/{id}/messages` - Get chat messages
- `POST /api/chats/{id}/messages` - Add message to chat

## License

MIT



