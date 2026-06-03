from typing import Optional, List

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    role: str
    module: str
    priority: str
    status: str
    source_type: str
    source_id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    action_path: str
    due_at: Optional[str] = None
    created_at: str
    metadata: dict = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    role: str
    generated_at: str
