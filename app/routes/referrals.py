from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.alert import Alert
from app.models.facility import Facility
from app.models.patient import Patient
from app.models.referral import Referral
from app.models.user import User
from app.schemas.referrals import ReferralCreate, ReferralResponse
from app.utils.dependencies import role_required
from app.utils.validators import Validators

router = APIRouter(prefix="/referrals", tags=["referrals"])


def _response(referral: Referral) -> ReferralResponse:
    return ReferralResponse(
        id=str(referral.id),
        facility_slug=referral.facility_slug,
        patient_id=str(referral.patient_id),
        from_department_id=referral.from_department_id,
        to_department_id=referral.to_department_id,
        reason=referral.reason,
        priority=referral.priority,
        notes=referral.notes,
        status=referral.status,
        created_by=str(referral.created_by),
        accepted_by=str(referral.accepted_by) if referral.accepted_by else None,
        completed_by=str(referral.completed_by) if referral.completed_by else None,
        created_at=referral.created_at.isoformat() if referral.created_at else "",
        updated_at=referral.updated_at.isoformat() if referral.updated_at else None,
        accepted_at=referral.accepted_at.isoformat() if referral.accepted_at else None,
        completed_at=referral.completed_at.isoformat() if referral.completed_at else None,
    )


def _facility_for_user(current_user: User) -> Facility:
    facility = db_session.query(Facility).filter_by(slug=current_user.facility_slug, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=403, detail="Your facility is inactive or not found")
    return facility


def _department_exists(facility: Facility, department_id: str) -> bool:
    return any(dept.get("id") == department_id for dept in (facility.departments or []))


def _notify_department(facility_slug: str, department_id: str, referral: Referral) -> None:
    recipients = (
        db_session.query(User)
        .filter(
            User.facility_slug == facility_slug,
            User.is_active == True,
            or_(User.department_id == department_id, User.role == "ADMIN"),
        )
        .all()
    )
    for recipient in recipients:
        db_session.add(Alert(
            facility_slug=facility_slug,
            alert_type="info",
            title="New department referral",
            message=f"A {referral.priority} referral is waiting: {referral.reason}",
            recipient_id=recipient.id,
        ))


@router.post("", response_model=ReferralResponse, status_code=status.HTTP_201_CREATED)
async def create_referral(
    data: ReferralCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db),
):
    facility = _facility_for_user(current_user)
    if not _department_exists(facility, data.to_department_id):
        raise HTTPException(status_code=404, detail="Receiving department not found")
    patient = db_session.query(Patient).filter_by(id=data.patient_id, facility_slug=facility.slug, is_active=True).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    referral = Referral(
        facility_id=facility.id,
        facility_slug=facility.slug,
        patient_id=patient.id,
        from_department_id=current_user.department_id or patient.department_id,
        to_department_id=data.to_department_id,
        reason=Validators.sanitize_string(data.reason),
        priority=data.priority,
        notes=Validators.sanitize_string(data.notes or "") if data.notes else None,
        status="pending",
        created_by=current_user.id,
    )
    db_session.add(referral)
    db_session.flush()
    _notify_department(facility.slug, data.to_department_id, referral)
    db_session.commit()
    db_session.refresh(referral)
    return _response(referral)


@router.get("", response_model=List[ReferralResponse])
async def get_referrals(
    department_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db),
):
    facility = _facility_for_user(current_user)
    query = db_session.query(Referral).filter_by(facility_slug=facility.slug)
    if current_user.role != "ADMIN":
        if not current_user.department_id:
            return []
        query = query.filter_by(to_department_id=current_user.department_id)
    elif department_id:
        query = query.filter_by(to_department_id=department_id)
    return [_response(referral) for referral in query.order_by(Referral.created_at.desc()).all()]


@router.put("/{referral_id}/accept", response_model=ReferralResponse)
async def accept_referral(
    referral_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db),
):
    facility = _facility_for_user(current_user)
    referral = db_session.query(Referral).filter_by(id=referral_id, facility_slug=facility.slug).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    if current_user.role != "ADMIN" and referral.to_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Cannot accept referral for another department")
    referral.status = "accepted"
    referral.accepted_by = current_user.id
    referral.accepted_at = datetime.utcnow()
    patient = db_session.query(Patient).filter_by(id=referral.patient_id, facility_slug=facility.slug).first()
    if patient:
        patient.department_id = referral.to_department_id
        db_session.add(patient)
    db_session.add(referral)
    db_session.commit()
    db_session.refresh(referral)
    return _response(referral)


@router.put("/{referral_id}/complete", response_model=ReferralResponse)
async def complete_referral(
    referral_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
    db: Session = Depends(get_db),
):
    facility = _facility_for_user(current_user)
    referral = db_session.query(Referral).filter_by(id=referral_id, facility_slug=facility.slug).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    if current_user.role != "ADMIN" and referral.to_department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Cannot complete referral for another department")
    referral.status = "completed"
    referral.completed_by = current_user.id
    referral.completed_at = datetime.utcnow()
    db_session.add(referral)
    db_session.commit()
    db_session.refresh(referral)
    return _response(referral)
