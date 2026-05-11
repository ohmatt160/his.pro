import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from app.extensions import Base, db_session


class BaseModel(Base):
    """Abstract base model with common fields and methods"""
    __abstract__ = True

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def save(self):
        """Save instance to database with error handling"""
        try:
            db_session.add(self)
            db_session.commit()
            return self
        except Exception as e:
            db_session.rollback()
            raise e

    def update(self, **kwargs):
        """Update instance with given kwargs"""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db_session.commit()
            return self
        except Exception as e:
            db_session.rollback()
            raise e

    def delete(self):
        """Delete instance from database"""
        try:
            db_session.delete(self)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e

    def to_dict(self):
        """Convert model to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO 8601 strings for JSON serialization
            if isinstance(value, datetime):
                result[column.name] = value.isoformat() if value else None
            else:
                result[column.name] = value
        return result
