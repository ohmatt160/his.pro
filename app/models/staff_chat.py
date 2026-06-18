from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class ChatConversation(BaseModel):
    """Two-person staff chat conversation scoped to one facility."""

    __tablename__ = "chat_conversations"

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    participant_ids = Column(JSON, nullable=False, default=list)
    last_message_at = Column(DateTime, default=datetime.utcnow, index=True)

    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(BaseModel):
    """Staff chat message scoped to one facility."""

    __tablename__ = "chat_messages"

    conversation_id = Column(String(36), ForeignKey("chat_conversations.id"), nullable=False, index=True)
    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    message_type = Column(String(20), nullable=False, default="text")
    file_name = Column(String(255), nullable=True)
    file_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(120), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)

    conversation = relationship("ChatConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])
