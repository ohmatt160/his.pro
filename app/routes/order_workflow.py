from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.order_workflow import OrderWorkflowEvent
from app.models.patient import Patient
from app.models.user import User
from app.schemas.order_workflow import OrderWorkflowEventResponse
from app.utils.dependencies import role_required

router = APIRouter(prefix="/order-workflow", tags=["order-workflow"])


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _response(event: OrderWorkflowEvent) -> OrderWorkflowEventResponse:
    return OrderWorkflowEventResponse(
        id=str(event.id),
        facility_slug=event.facility_slug,
        patient_id=str(event.patient_id) if event.patient_id else None,
        order_type=event.order_type,
        order_id=str(event.order_id),
        event_type=event.event_type,
        status=event.status,
        title=event.title,
        message=event.message,
        actor_id=str(event.actor_id) if event.actor_id else None,
        target_role=event.target_role,
        metadata=event.metadata_json or {},
        occurred_at=event.occurred_at.isoformat() if event.occurred_at else "",
        created_at=event.created_at.isoformat() if event.created_at else "",
    )


@router.get("", response_model=List[OrderWorkflowEventResponse])
async def list_order_workflow_events(
    patient_id: Optional[str] = Query(None),
    order_type: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "LAB_TECH", "PHARMACIST")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    query = db_session.query(OrderWorkflowEvent).filter_by(facility_slug=facility_slug)
    if patient_id:
        patient = db_session.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        query = query.filter_by(patient_id=patient_id)
    if order_type:
        query = query.filter_by(order_type=order_type)
    if order_id:
        query = query.filter_by(order_id=order_id)
    if event_type:
        query = query.filter_by(event_type=event_type)

    events = query.order_by(OrderWorkflowEvent.occurred_at.desc()).limit(300).all()
    return [_response(event) for event in events]

