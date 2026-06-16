from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.models.user import User
from app.schemas.patient_notifications import (
    PatientNotificationMarkSent,
    PatientNotificationResponse,
)
from app.services.patient_notification_service import PatientNotificationService
from app.utils.dependencies import role_required

router = APIRouter(prefix="/patient-notifications", tags=["patient-notifications"])


def _response(notification: PatientNotification) -> PatientNotificationResponse:
    return PatientNotificationResponse(
        id=str(notification.id),
        facility_slug=notification.facility_slug,
        patient_id=str(notification.patient_id),
        notification_type=notification.notification_type,
        channel=notification.channel,
        title=notification.title,
        message=notification.message,
        recipient_phone=notification.recipient_phone,
        recipient_email=notification.recipient_email,
        status=notification.status,
        source_type=notification.source_type,
        source_id=notification.source_id,
        metadata=notification.metadata_json or {},
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat() if notification.created_at else "",
        updated_at=notification.updated_at.isoformat() if notification.updated_at else None,
    )


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _get_notification(notification_id: str, facility_slug: str) -> PatientNotification:
    notification = db_session.query(PatientNotification).filter_by(
        id=notification_id,
        facility_slug=facility_slug,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("", response_model=List[PatientNotificationResponse])
async def list_patient_notifications(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    channel: Optional[str] = Query(None),
    notification_type: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    query = db_session.query(PatientNotification).filter_by(facility_slug=facility_slug)
    if patient_id:
        patient = db_session.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return []
        query = query.filter_by(patient_id=patient_id)
    if status_filter:
        query = query.filter_by(status=status_filter.upper())
    if channel:
        query = query.filter_by(channel=channel.upper())
    if notification_type:
        query = query.filter_by(notification_type=notification_type)

    notifications = query.order_by(PatientNotification.created_at.desc()).limit(200).all()
    return [_response(notification) for notification in notifications]


@router.put("/{notification_id}/sent", response_model=PatientNotificationResponse)
async def mark_patient_notification_sent(
    notification_id: str,
    data: PatientNotificationMarkSent,
    current_user: User = Depends(role_required("ADMIN", "RECEPTIONIST")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    notification = _get_notification(notification_id, facility_slug)
    if notification.status == "SUPPRESSED":
        raise HTTPException(status_code=400, detail="Suppressed notifications cannot be marked sent")
    updated = PatientNotificationService.mark_sent(notification, data.provider_message_id)
    db_session.commit()
    db_session.refresh(updated)
    return _response(updated)


@router.put("/{notification_id}/read", response_model=PatientNotificationResponse)
async def mark_patient_notification_read(
    notification_id: str,
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    notification = _get_notification(notification_id, facility_slug)
    updated = PatientNotificationService.mark_read(notification)
    db_session.commit()
    db_session.refresh(updated)
    return _response(updated)
