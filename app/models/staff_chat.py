from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class ChatConversation(BaseModel):
    """Two-person staff chat conversation scoped to one facility."""

    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("idx_chat_conversations_facility_participant", "facility_slug", "participant_key", unique=True),
        Index("idx_chat_conversations_facility_last_message", "facility_slug", "last_message_at"),
    )

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    participant_ids = Column(JSON, nullable=False, default=list)
    participant_key = Column(String(80), nullable=True)
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
    __table_args__ = (
        Index(
            "idx_chat_messages_conversation_created",
            "facility_slug",
            "conversation_id",
            "created_at",
        ),
        Index(
            "idx_chat_messages_unread",
            "facility_slug",
            "conversation_id",
            "is_read",
            "sender_id",
        ),
    )

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
