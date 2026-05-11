"""
Alert Routes - FastAPI Version
Converted from Flask-RESTx alert_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db, db_session
from app.utils.dependencies import get_current_user, role_required
from app.utils.validators import Validators
from app.models.user import User
from app.models.alert import Alert

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    facility_slug: Optional[str] = Field(None)  # if None, use user's facility
    alert_type: str = Field(..., pattern="^(info|warning|critical)$")
    title: str = Field(..., max_length=200)
    message: str = Field(...)
    recipient_id: Optional[str] = Field(None)
    expires_at: Optional[str] = Field(None)  # ISO datetime string


class AlertUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = Field(None)
    alert_type: Optional[str] = Field(None, pattern="^(info|warning|critical)$")


class AlertResponse(BaseModel):
    id: str
    facility_slug: str
    alert_type: str
    title: str
    message: str
    recipient_id: Optional[str]
    recipient_name: Optional[str]
    is_read: bool
    read_at: Optional[str]
    expires_at: Optional[str]
    created_at: str


class MessageResponse(BaseModel):
    message: str


@router.get("", response_model=List[AlertResponse])
async def get_alerts(
    is_read: Optional[bool] = Query(None),
    alert_type: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Paginated list of alerts for user's facility"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    query = db_session.query(Alert).filter_by(facility_slug=facility_slug)

    # Filter by user: see own alerts and facility-wide (recipient_id=None)
    query = query.filter(
        (Alert.recipient_id == current_user.id) | (Alert.recipient_id == None)
    )

    if is_read is not None:
        query = query.filter_by(is_read=is_read)
    if alert_type:
        query = query.filter_by(alert_type=alert_type)

    query = query.order_by(Alert.created_at.desc())

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    result = []
    for alert in items:
        recipient_name = f"{alert.recipient.first_name} {alert.recipient.last_name}".strip() if alert.recipient else None
        result.append(AlertResponse(
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
        ))

    return result


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: AlertCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """Create a new alert"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Validate alert type
    if data.alert_type not in Alert.ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid alert_type. Must be one of: {', '.join(Alert.ALERT_TYPES)}")

    # Validate recipient if provided
    recipient_id = data.recipient_id
    if recipient_id:
        recipient = db_session.query(User).filter_by(id=recipient_id).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        if recipient.facility_slug != facility_slug:
            raise HTTPException(status_code=404, detail="Recipient not found")

    # Parse expiry
    expires_at = None
    if data.expires_at:
        try:
            # Handle ISO format with possible Z suffix
            expires_str = data.expires_at.replace('Z', '+00:00')
            expires_at = datetime.fromisoformat(expires_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO 8601 format")

    alert = Alert(
        facility_slug=facility_slug,
        alert_type=data.alert_type,
        title=data.title,
        message=data.message,
        recipient_id=recipient_id,
        expires_at=expires_at
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

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


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Get alert by ID"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = db_session.query(Alert).filter_by(id=alert_id, facility_slug=facility_slug).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

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


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    data: AlertUpdate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    """Update alert"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = db_session.query(Alert).filter_by(id=alert_id, facility_slug=facility_slug).first()
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

    alert = db_session.query(Alert).filter_by(id=alert_id, facility_slug=facility_slug).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_session.delete(alert)
    db_session.commit()

    return MessageResponse(message="Alert deleted successfully")


@router.put("/{alert_id}/read", response_model=AlertResponse)
async def mark_as_read(
    alert_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Mark alert as read"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = db_session.query(Alert).filter_by(id=alert_id, facility_slug=facility_slug).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.mark_as_read()
    alert.save()
    db_session.commit()

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


@router.put("/{alert_id}/unread", response_model=AlertResponse)
async def mark_as_unread(
    alert_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db)
):
    """Mark alert as unread"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    alert = db_session.query(Alert).filter_by(id=alert_id, facility_slug=facility_slug).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.mark_as_unread()
    alert.save()
    db_session.commit()

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
