from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from .core.database import init_db
from .core.logging_config import setup_logging
from .api.routes import auth, modules, chats, agent
from .api.exceptions import (
    canon_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from .exceptions import CanonException
from .config import settings

# Setup logging first
setup_logging()

app = FastAPI(title="Canon API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(CanonException, canon_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

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
