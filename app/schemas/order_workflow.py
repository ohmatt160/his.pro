from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class OrderWorkflowEventResponse(BaseModel):
    id: str
    facility_slug: str
    patient_id: Optional[str] = None
    order_type: str
    order_id: str
    event_type: str
    status: str
    title: str
    message: Optional[str] = None
    actor_id: Optional[str] = None
    target_role: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: str
    created_at: str

