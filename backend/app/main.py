from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .api.routes import auth, modules, chats, agent

app = FastAPI(title="Canon API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(chats.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Canon API"}


@app.get("/health")
def health():
    return {"status": "healthy"}



