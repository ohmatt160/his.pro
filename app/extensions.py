"""
Database Extensions for FastAPI
SQLAlchemy direct integration (no Flask-SQLAlchemy)
"""

from sqlalchemy import create_engine, MetaData, Column, String, DateTime, Date, ForeignKey, Integer, Boolean, Text, JSON, Numeric
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
