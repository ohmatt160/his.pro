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
from app.utils.branch_scope import ensure_patient_branch_access, require_facility_slug, require_tenant_row, tenant_query
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility
from app.models.lab import LabOrder, LabResult

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


def _lab_order_response(order, result=None) -> LabOrderResponse:
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
        department_id=order.department_id,
        branch_id=order.branch_id or order.department_id,
        result=_lab_result_response(result) if result else None,
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'LAB_TECH', 'DOCTOR')),
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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'LAB_TECH', 'DOCTOR')),
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
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None, max_length=36),
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)
    query = tenant_query(db, LabOrder, current_user, branch_id)

    if patient_id:
        # Verify patient belongs to facility
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            return []
        ensure_patient_branch_access(patient, current_user, branch_id)
        query = query.filter_by(patient_id=patient_id)
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(LabOrder.status.in_(["PENDING", "COLLECTED", "IN_PROGRESS", "COMPLETED"]))
    orders = (
        query.order_by(LabOrder.order_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    order_ids = [order.id for order in orders]
    results_by_order_id = {
        result.order_id: result
        for result in (
            db.query(LabResult)
            .join(LabOrder, LabOrder.id == LabResult.order_id)
            .filter(
                LabResult.order_id.in_(order_ids),
                LabOrder.facility_slug == facility_slug,
            )
            .all()
            if order_ids
            else []
        )
    }

    return [_lab_order_response(o, results_by_order_id.get(o.id)) for o in orders]


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    data: LabOrderCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)

    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    branch_id = ensure_patient_branch_access(patient, current_user, data.branch_id or data.department_id)

    test = LabService.get_lab_test_by_id(data.test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    payload = data.model_dump()
    payload['facility_slug'] = facility_slug
    payload['branch_id'] = branch_id or patient.branch_id or patient.department_id
    payload['department_id'] = branch_id or patient.department_id

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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    order = LabService.get_lab_order_by_id(order_id)
    require_tenant_row(order, current_user, "Lab order not found")

    return _lab_order_response(order)


@router.put("/orders/{order_id}", response_model=LabOrderResponse)
async def update_lab_order_status(
    order_id: str,
    data: LabOrderUpdate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)
    order = LabService.get_lab_order_by_id(order_id)
    require_tenant_row(order, current_user, "Lab order not found")

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
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'DOCTOR', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    order = LabService.get_lab_order_by_id(order_id)
    require_tenant_row(order, current_user, "Lab order not found")

    result = LabService.get_result_by_order(order_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")

    return _lab_result_response(result)


@router.post("/results/{order_id}", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    order_id: str,
    data: LabResultCreate,
    current_user: User = Depends(role_required('ADMIN', 'BRANCH_ADMIN', 'LAB_TECH')),
    db: Session = Depends(get_db)
):
    facility_slug = require_facility_slug(current_user)
    order = LabService.get_lab_order_by_id(order_id)
    require_tenant_row(order, current_user, "Lab order not found")

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
