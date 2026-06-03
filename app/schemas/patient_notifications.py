from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PatientNotificationResponse(BaseModel):
    id: str
    facility_slug: str
    patient_id: str
    notification_type: str
    channel: str
    title: str
    message: str
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    status: str
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sent_at: Optional[str] = None
    read_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class PatientNotificationMarkSent(BaseModel):
    provider_message_id: Optional[str] = Field(None, max_length=160)

