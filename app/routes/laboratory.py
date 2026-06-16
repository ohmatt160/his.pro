"""
Laboratory Routes - FastAPI Version
Converted from Flask-RESTx lab_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.schemas.laboratory import LabTestResponse, LabTestCreate, LabOrderResponse, LabOrderCreate, LabOrderUpdate, \
    LabResultResponse, LabResultCreate
from app.services.clinical_workflow_service import ClinicalWorkflowService
from app.services.lab_service import LabService
from app.services.order_workflow_service import OrderWorkflowService
from app.services.patient_notification_service import PatientNotificationService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/laboratory", tags=["laboratory"])


def _lab_test_response(test) -> LabTestResponse:
    return LabTestResponse(
        id=str(test.id),
        name=test.name,
        code=test.code,
        description=test.description,
        category=test.category,
        unit=test.unit,
        reference_range=test.reference_range,
        price=float(test.price) if test.price is not None else None,
        is_active=test.is_active,
        created_at=test.created_at.isoformat() if test.created_at else "",
        updated_at=test.updated_at.isoformat() if test.updated_at else None
    )


def _lab_order_response(order) -> LabOrderResponse:
    return LabOrderResponse(
        id=str(order.id),
        patient_id=str(order.patient_id),
        test_id=str(order.test_id),
        ordered_by=str(order.ordered_by),
        status=order.status,
        priority=order.priority,
        notes=order.notes,
        completed_at=order.completed_date.isoformat() if order.completed_date else None,
        facility_slug=order.facility_slug,
        created_at=order.created_at.isoformat() if order.created_at else "",
        updated_at=order.updated_at.isoformat() if order.updated_at else None
    )


def _lab_result_response(result) -> LabResultResponse:
    return LabResultResponse(
        id=str(result.id),
        order_id=str(result.order_id),
        entered_by=None,
        value=result.value,
        is_abnormal=result.is_abnormal,
        notes=result.notes,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else None
    )


# ==================== Lab Tests ====================

@router.get("/tests", response_model=List[LabTestResponse])
async def get_lab_tests(
    active_only: bool = Query(True),
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    tests = LabService.get_all_lab_tests(active_only=active_only)
    return [_lab_test_response(t) for t in tests]


@router.post("/tests", response_model=LabTestResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_test(
    data: LabTestCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    test, error = LabService.create_lab_test(data.model_dump())
    if error:
        raise HTTPException(status_code=400, detail=error)

    return _lab_test_response(test)


@router.get("/tests/{test_id}", response_model=LabTestResponse)
async def get_lab_test(
    test_id: str,
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    test = LabService.get_lab_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    return _lab_test_response(test)


@router.put("/tests/{test_id}", response_model=LabTestResponse)
async def update_lab_test(
    test_id: str,
    data: LabTestCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    test = LabService.get_lab_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    updated_test = LabService.update_lab_test(test, data.model_dump(exclude_unset=True))

    return _lab_test_response(updated_test)


# ==================== Lab Orders ====================

@router.get("/orders", response_model=List[LabOrderResponse])
async def get_lab_orders(
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if patient_id:
        # Verify patient belongs to facility
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return []
        orders = LabService.get_lab_orders_by_patient(patient_id, facility_slug)
    elif status:
        orders = LabService.get_lab_orders_by_status(status, facility_slug)
    else:
        orders = []
        for order_status in ["PENDING", "COLLECTED", "IN_PROGRESS", "COMPLETED"]:
            orders.extend(LabService.get_lab_orders_by_status(order_status, facility_slug))

    return [_lab_order_response(o) for o in orders]


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    data: LabOrderCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    test = LabService.get_lab_test_by_id(data.test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    payload = data.model_dump()
    payload['facility_slug'] = facility_slug

    order = LabService.create_lab_order(payload, current_user.id)
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=order.patient_id,
        order_type="lab",
        order_id=order.id,
        event_type="consultation_order_created",
        status=order.status,
        title="Lab order created",
        message=f"Lab order created for test {test.name}.",
        actor_id=current_user.id,
        target_role="LAB_TECH",
        metadata={"test_id": test.id, "test_name": test.name},
    )

    return _lab_order_response(order)


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
async def get_lab_order(
    order_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    return _lab_order_response(order)


@router.put("/orders/{order_id}", response_model=LabOrderResponse)
async def update_lab_order_status(
    order_id: str,
    data: LabOrderUpdate,
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    if not data.status:
        raise HTTPException(status_code=400, detail="Status is required")

    previous_status = order.status
    updated_order = LabService.update_lab_order_status(order, data.status)
    if updated_order.status == "COLLECTED" and previous_status != "COLLECTED":
        OrderWorkflowService.record(
            facility_slug=facility_slug,
            patient_id=updated_order.patient_id,
            order_type="lab",
            order_id=updated_order.id,
            event_type="lab_sample_collected",
            status=updated_order.status,
            title="Lab sample collected",
            message="Lab sample has been collected.",
            actor_id=current_user.id,
            target_role="LAB_TECH",
            metadata={"test_id": updated_order.test_id},
        )

    return _lab_order_response(updated_order)


# ==================== Lab Results ====================

@router.get("/results/{order_id}", response_model=LabResultResponse)
async def get_lab_result(
    order_id: str,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    result = LabService.get_result_by_order(order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")

    return _lab_result_response(result)


@router.post("/results/{order_id}", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    order_id: str,
    data: LabResultCreate,
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    if order.status == 'COMPLETED':
        raise HTTPException(status_code=400, detail="Lab order already completed")

    result = LabService.create_lab_result(order_id, data.model_dump())
    patient = db.query(Patient).filter_by(id=order.patient_id, facility_slug=facility_slug).first()
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=order.patient_id,
        order_type="lab",
        order_id=order.id,
        event_type="lab_result_released",
        status="COMPLETED",
        title="Lab result released",
        message=f"Result released for {order.test.name if order.test else 'lab order'}.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"result_id": result.id, "is_abnormal": result.is_abnormal},
    )
    if patient:
        PatientNotificationService.create(
            facility_slug=facility_slug,
            patient=patient,
            notification_type="lab_result_ready",
            title="Lab result ready",
            message="Your lab result is ready. Please contact your care team for review.",
            source_type="lab_order",
            source_id=order.id,
            metadata={"result_id": result.id, "is_abnormal": result.is_abnormal},
        )
    ClinicalWorkflowService.notify_user(
        order.ordered_by,
        facility_slug,
        "info",
        "Lab result ready",
        f"A lab result is ready for order {order.id}",
    )
    OrderWorkflowService.record(
        facility_slug=facility_slug,
        patient_id=order.patient_id,
        order_type="lab",
        order_id=order.id,
        event_type="doctor_notified",
        status="NOTIFIED",
        title="Doctor notified",
        message="Ordering clinician was notified that the lab result is ready.",
        actor_id=current_user.id,
        target_role="DOCTOR",
        metadata={"ordered_by": order.ordered_by},
    )

    return _lab_result_response(result)
