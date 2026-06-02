"""
Audit Log Routes - FastAPI Version
Converted from Flask-RESTx audit_log_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.audit_logs import AuditLogResponse
from app.services.audit_log_service import  AuditLogService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _audit_log_response(log) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(log.id),
        user_id=str(log.user_id) if log.user_id else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=str(log.resource_id) if log.resource_id else None,
        details=log.details or {},
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        facility_slug=log.facility_slug,
        created_at=log.created_at.isoformat() if log.created_at else ""
    )




@router.get("", response_model=List[AuditLogResponse])
async def get_audit_logs(
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get audit logs (admin only)"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    result = AuditLogService.get_logs(
        facility_slug=facility_slug,
        action=action,
        resource_type=resource_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    logs = result['items']
    return [_audit_log_response(log) for log in logs]


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Get single audit log entry (admin only)"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    log = AuditLogService.get_log_by_id(log_id, facility_slug)

    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return _audit_log_response(log)
