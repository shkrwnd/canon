import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.config import settings

# Workaround for Starlette 0.50.0 + httpx compatibility issue
# Starlette's TestClient tries to pass 'app' to httpx.Client which doesn't accept it
# We'll use httpx directly with ASGITransport as a fallback
import httpx
from httpx import ASGITransport
import asyncio

class CompatibleTestClient:
    """Compatible test client that works around httpx/Starlette version issues"""
    def __init__(self, app):
        self.app = app
        self.transport = ASGITransport(app=app)
        self.base_url = "http://testserver"
    
    def _run_async(self, coro):
        """Run async coroutine in event loop"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
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

# Use CompatibleTestClient instead of FastAPI's TestClient to avoid version conflicts
TestClient = CompatibleTestClient

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Create a test client"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    # Use CompatibleTestClient to avoid Starlette/httpx version conflicts
    yield TestClient(app)
    app.dependency_overrides.clear()



