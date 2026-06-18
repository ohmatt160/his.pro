from typing import List, Optional

from pydantic import BaseModel, Field


class ChatStaffResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_online: bool
    last_active: Optional[str] = None


class ConversationCreate(BaseModel):
    participant_id: str = Field(..., min_length=1, max_length=36)


class ChatSenderResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str


class ChatMessageCreate(BaseModel):
    content: Optional[str] = Field(None, max_length=5000)
    message_type: str = Field("text", pattern="^(text|file|image)$")
    file_name: Optional[str] = Field(None, max_length=255)
    file_url: Optional[str] = Field(None, max_length=500)
    file_size: Optional[int] = Field(None, ge=0, le=10 * 1024 * 1024)
    file_type: Optional[str] = Field(None, max_length=120)


class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: str
    facility_slug: str
    sender_id: str
    sender: ChatSenderResponse
    content: Optional[str]
    message_type: str
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    created_at: str


class ChatConversationResponse(BaseModel):
    id: str
    facility_slug: str
    participant_ids: List[str]
    other_staff: ChatStaffResponse
    last_message: Optional[ChatMessageResponse] = None
    unread_count: int
    last_message_at: Optional[str] = None
    created_at: str


class ChatUploadResponse(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    file_type: str


class ChatUnreadCountResponse(BaseModel):
    unread_count: int
