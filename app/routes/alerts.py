"""
Alert Routes - FastAPI Version
Converted from Flask-RESTx alert_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db, db_session
from app.schemas.alerts import AlertResponse, AlertCreate, AlertUpdate, RoleAlertCreate
from app.schemas.users import MessageResponse
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.alert import Alert
from app.services.audit_log_service import AuditLogService
from app.utils.branch_scope import belongs_to_branch, user_branch_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])
ALERT_VIEW_ROLES = ('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST', 'PHARMACIST', 'LAB_TECH')
ALERT_CREATE_ROLES = ('ADMIN', 'BRANCH_ADMIN', 'DOCTOR')


def _alert_response(alert: Alert) -> AlertResponse:
    recipient_name = f"{alert.recipient.first_name} {alert.recipient.last_name}".strip() if alert.recipient else None
    return AlertResponse(
        id=str(alert.id),
        facility_slug=alert.facility_slug,
        alert_type=alert.alert_type,
        title=alert.title,
        message=alert.message,
        recipient_id=str(alert.recipient_id) if alert.recipient_id else None,
        recipient_name=recipient_name,
        is_read=alert.is_read,
        read_at=alert.read_at.isoformat() if alert.read_at else None,
        expires_at=alert.expires_at.isoformat() if alert.expires_at else None,
        created_at=alert.created_at.isoformat() if alert.created_at else ""
    )


def _visible_alert_query(current_user: User):
    query = db_session.query(Alert).options(joinedload(Alert.recipient)).filter(
        Alert.facility_slug == current_user.facility_slug,
        or_(Alert.expires_at == None, Alert.expires_at > datetime.utcnow()),
    )
    if current_user.role == "ADMIN":
        return query.filter(or_(Alert.recipient_id == current_user.id, Alert.recipient_id == None))
    return query.filter(Alert.recipient_id == current_user.id)


def _ensure_alert_recipient_allowed(recipient: User | None, current_user: User):
    if not recipient or recipient.facility_slug != current_user.facility_slug:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if current_user.role != "ADMIN" and not belongs_to_branch(recipient, user_branch_id(current_user)):
        raise HTTPException(status_code=404, detail="Recipient not found")


def _parse_expiry(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601 format")


@router.get("", response_model=List[AlertResponse])
async def get_alerts(
    is_read: Optional[bool] = Query(None),
    alert_type: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required(*ALERT_VIEW_ROLES)),
    db: Session = Depends(get_db)
):
    """Paginated list of alerts for user's facility"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    query = _visible_alert_query(current_user)

    if is_read is not None:
        query = query.filter_by(is_read=is_read)
    if alert_type:
        query = query.filter_by(alert_type=alert_type)

    query = query.order_by(Alert.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return [_alert_response(alert) for alert in items]


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    request: Request,
    current_user: User = Depends(role_required(*ALERT_CREATE_ROLES)),
    db: Session = Depends(get_db)
):
    """Create a new alert"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Validate alert type
    if data.alert_type not in Alert.ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid alert_type. Must be one of: {', '.join(Alert.ALERT_TYPES)}")

    recipient_id = data.recipient_id
    if current_user.role != "ADMIN" and not recipient_id:
        raise HTTPException(status_code=400, detail="Select a recipient for branch alerts")
    if recipient_id:
        recipient = db_session.query(User).filter_by(id=recipient_id).first()
        _ensure_alert_recipient_allowed(recipient, current_user)

    expires_at = _parse_expiry(data.expires_at)

    alert = Alert(
        facility_slug=facility_slug,
        alert_type=data.alert_type,
        title=Validators.sanitize_string(data.title),
        message=Validators.sanitize_string(data.message),
        recipient_id=recipient_id,
        expires_at=expires_at
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="CREATE_ALERT",
        resource_type="alert",
        resource_id=alert.id,
        facility_slug=facility_slug,
        details={
            "alert_type": alert.alert_type,
            "recipient_id": alert.recipient_id,
            "title": alert.title,
        },
        request=request,
    )

    return _alert_response(alert)


@router.post("/role", response_model=List[AlertResponse], status_code=status.HTTP_201_CREATED)
async def create_role_alert(
    data: RoleAlertCreate,
    request: Request,
    current_user: User = Depends(role_required(*ALERT_CREATE_ROLES)),
    db: Session = Depends(get_db)
):
    """Create the same alert for every active staff member with a role."""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    recipients = db_session.query(User).filter_by(
        facility_slug=facility_slug,
        role=data.recipient_role,
        is_active=True,
    )
    if current_user.role != "ADMIN":
        branch_id = user_branch_id(current_user)
        recipients = recipients.filter(or_(User.branch_id == branch_id, User.department_id == branch_id))
    recipients = recipients.all()
    if not recipients:
        raise HTTPException(status_code=404, detail="No active users found for this role")

    alerts = []
    expires_at = _parse_expiry(data.expires_at)
    for recipient in recipients:
        alert = Alert(
            facility_slug=facility_slug,
            alert_type=data.alert_type,
            title=Validators.sanitize_string(data.title),
            message=Validators.sanitize_string(data.message),
            recipient_id=recipient.id,
            expires_at=expires_at,
        )
        db_session.add(alert)
        alerts.append(alert)
    db_session.commit()
    for alert in alerts:
        db_session.refresh(alert)

    AuditLogService.log_action(
        user_id=current_user.id,
        action="CREATE_ROLE_ALERT",
        resource_type="alert",
        resource_id=None,
        facility_slug=facility_slug,
        details={"recipient_role": data.recipient_role, "count": len(alerts), "title": data.title},
        request=request,
    )

    return [_alert_response(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(role_required(*ALERT_VIEW_ROLES)),
    db: Session = Depends(get_db)
):
    """Get alert by ID"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = _visible_alert_query(current_user).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return _alert_response(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    data: AlertUpdate,
    current_user: User = Depends(role_required(*ALERT_CREATE_ROLES)),
    db: Session = Depends(get_db)
):
    """Update alert"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = _visible_alert_query(current_user).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if data.title is not None:
        alert.title = Validators.sanitize_string(data.title)
    if data.message is not None:
        alert.message = Validators.sanitize_string(data.message)
    if data.alert_type is not None:
        if data.alert_type not in Alert.ALERT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid alert_type. Must be one of: {', '.join(Alert.ALERT_TYPES)}")
        alert.alert_type = data.alert_type

    alert.save()
    db_session.commit()

    return _alert_response(alert)


@router.delete("/{alert_id}", response_model=MessageResponse)
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    """Delete alert"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = _visible_alert_query(current_user).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_session.delete(alert)
    db_session.commit()

    return MessageResponse(message="Alert deleted successfully")


@router.put("/{alert_id}/read", response_model=AlertResponse)
async def mark_as_read(
    alert_id: str,
    current_user: User = Depends(role_required(*ALERT_VIEW_ROLES)),
    db: Session = Depends(get_db)
):
    """Mark alert as read"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = _visible_alert_query(current_user).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.mark_as_read()
    alert.save()
    db_session.commit()

    return _alert_response(alert)


@router.put("/actions/mark-all-read", response_model=MessageResponse)
async def mark_all_as_read(
    current_user: User = Depends(role_required(*ALERT_VIEW_ROLES)),
    db: Session = Depends(get_db)
):
    """Mark all visible unread alerts as read."""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alerts = _visible_alert_query(current_user).filter(Alert.is_read == False).all()
    for alert in alerts:
        alert.mark_as_read()
        db_session.add(alert)
    db_session.commit()
    return MessageResponse(message=f"Marked {len(alerts)} alert(s) as read")


@router.put("/{alert_id}/unread", response_model=AlertResponse)
async def mark_as_unread(
    alert_id: str,
    current_user: User = Depends(role_required(*ALERT_VIEW_ROLES)),
    db: Session = Depends(get_db)
):
    """Mark alert as unread"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = _visible_alert_query(current_user).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.mark_as_unread()
    alert.save()
    db_session.commit()

    return _alert_response(alert)
