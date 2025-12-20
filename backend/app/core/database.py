from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from ..config import settings
import logging

logger = logging.getLogger(__name__)

# Configure SQLite connection args with timeout for better concurrency handling
sqlite_connect_args = {}
if "sqlite" in settings.database_url:
    sqlite_connect_args = {
        "check_same_thread": False,
        "timeout": 30.0,  # Wait up to 30 seconds for lock to be released
    }

engine = create_engine(
    settings.database_url,
    connect_args=sqlite_connect_args,
    echo=settings.debug if hasattr(settings, "debug") else False,
    pool_pre_ping=True,  # Verify connections before using
)

# Enable WAL mode for SQLite to improve concurrency
# WAL allows multiple readers and a single writer simultaneously
if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable WAL mode and set busy timeout for SQLite connections"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds in milliseconds
        cursor.close()
        logger.debug("SQLite WAL mode and busy timeout enabled")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_transaction():
    """Context manager for database transactions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
