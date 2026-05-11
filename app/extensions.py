"""
Database Extensions for FastAPI
Converted from Flask-SQLAlchemy to SQLAlchemy 2.0+
"""

from sqlalchemy import create_engine, MetaData, Column, String, DateTime, Date, ForeignKey, Integer, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./hispro.db')

# Create engine with connection pooling for scalability
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create scoped session for request/task safety
db_session = scoped_session(SessionLocal)

# Base class for models
Base = declarative_base()
Base.metadata = MetaData()

# query_property is not available in SQLAlchemy 2.0+, using session directly
# Base.query = db_session.query_property()

# Create a db-like object for compatibility with BaseModel pattern
class DB:
    Model = Base
    session = db_session
    Column = Column
    String = String
    DateTime = DateTime
    Date = Date
    ForeignKey = ForeignKey
    Integer = Integer
    Boolean = Boolean
    Text = Text
    JSON = JSON
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
