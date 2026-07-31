from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.extensions import get_db
from app.models.user import User
from app.schemas.tasks import TaskListResponse
from app.services.task_service import TaskService, normalize_task_role
from app.utils.branch_scope import user_branch_id
from app.utils.dependencies import role_required

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    role: Optional[str] = Query(None, max_length=50),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(
        role_required("ADMIN", "DOCTOR", "NURSE", "LAB_TECH", "PHARMACIST", "RECEPTIONIST", "BILLING")
    ),
    db: Session = Depends(get_db),
):
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    requested_role = normalize_task_role(role or current_user.role)
    if current_user.role != "ADMIN" and requested_role != current_user.role:
        raise HTTPException(status_code=403, detail="Cannot view another role's task queue")

    tasks = TaskService.get_tasks_for_role(
        facility_slug=current_user.facility_slug,
        role=requested_role,
        limit=limit,
        branch_id=None if current_user.role == "ADMIN" else user_branch_id(current_user),
    )

    return TaskListResponse(
        tasks=tasks,
        total=len(tasks),
        role=requested_role,
        generated_at=datetime.utcnow().isoformat(),
    )
