"""
Database Extensions for FastAPI
SQLAlchemy direct integration (no Flask-SQLAlchemy)
"""

from sqlalchemy import create_engine, MetaData, Column, String, DateTime, Date, ForeignKey, Integer, Boolean, Text, JSON, Numeric, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
import os
import logging
import time
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./hispro.db')
DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '40'))
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '10'))
DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
SLOW_QUERY_SECONDS = float(os.getenv('SLOW_QUERY_SECONDS', '0.5'))

# Create engine with connection pooling for scalability
# SQLite needs special handling
if 'sqlite' in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        echo=False
    )


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start_times = conn.info.get("query_start_time")
    if not start_times:
        return
    elapsed = time.perf_counter() - start_times.pop()
    if elapsed >= SLOW_QUERY_SECONDS:
        compact_statement = " ".join(str(statement).split())
        logger.warning("Slow database query %.3fs: %s", elapsed, compact_statement[:1000])

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for request/task safety
db_session = scoped_session(SessionLocal)

# Base class for declarative models
Base = declarative_base()
Base.metadata = MetaData()

# Add query property to Base for Flask-SQLAlchemy-style access
class _QueryProperty:
    """Descriptor to provide Model.query -> db_session.query(Model)"""
    def __init__(self, session):
        self.session = session
    def __get__(self, obj, owner):
        return self.session.query(owner)

Base.query = _QueryProperty(db_session)
class DB:
    """Compatibility wrapper providing db.Model, db.session, and type access"""
    Model = Base
    session = db_session
    # Expose column types for any code that still uses db.Column etc.
    Column = Column
    String = String
    DateTime = DateTime
    Date = Date
    ForeignKey = ForeignKey
    Integer = Integer
    Boolean = Boolean
    Text = Text
    JSON = JSON
    Numeric = Numeric
    relationship = relationship

db = DB()


def get_db():
    """
    Dependency to get the current database session.
    Returns the scoped_session which is managed by middleware.
    """
    return db_session


# For backward compatibility with existing code
def init_app(app):
    """
    Initialize database with FastAPI app
    (Kept for compatibility with existing init pattern)
    """
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    return engine
