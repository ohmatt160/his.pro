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
from app.services.lab_service import LabService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User
from app.models.patient import Patient
from app.models.facility import Facility

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/laboratory", tags=["laboratory"])


class LabTestCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=50)
    unit: Optional[str] = Field(None, max_length=20)
    reference_range: Optional[str] = Field(None)
    price: Optional[float] = Field(None, ge=0)


class LabTestResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str]
    category: Optional[str]
    unit: Optional[str]
    reference_range: Optional[str]
    price: Optional[float]
    is_active: bool
    created_at: str
    updated_at: Optional[str]


class LabOrderCreate(BaseModel):
    patient_id: str = Field(...)
    test_id: str = Field(...)
    priority: Optional[str] = Field(None, pattern="^(ROUTINE|URGENT|STAT)$")
    notes: Optional[str] = Field(None)
    order_date: Optional[str] = Field(None)


class LabOrderUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(PENDING|COLLECTED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class LabOrderResponse(BaseModel):
    id: str
    patient_id: str
    test_id: str
    ordered_by: str
    status: str
    priority: Optional[str]
    notes: Optional[str]
    completed_at: Optional[str]
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]


class LabResultCreate(BaseModel):
    value: Optional[str] = Field(None)
    is_abnormal: Optional[bool] = Field(False)
    notes: Optional[str] = Field(None)


class LabResultResponse(BaseModel):
    id: str
    order_id: str
    entered_by: Optional[str]
    value: Optional[str]
    is_abnormal: Optional[bool]
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


# ==================== Lab Tests ====================

@router.get("/tests", response_model=List[LabTestResponse])
async def get_lab_tests(
    active_only: bool = Query(True),
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    tests = LabService.get_all_lab_tests(active_only=active_only)
    return [
        LabTestResponse(
            id=str(t.id),
            name=t.name,
            code=t.code,
            description=t.description,
            category=t.category,
            unit=t.unit,
            reference_range=t.reference_range,
            price=t.price,
            is_active=t.is_active,
            created_at=t.created_at.isoformat() if t.created_at else "",
            updated_at=t.updated_at.isoformat() if t.updated_at else None
        ) for t in tests
    ]


@router.post("/tests", response_model=LabTestResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_test(
    data: LabTestCreate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db)
):
    test, error = LabService.create_lab_test(data.dict())
    if error:
        raise HTTPException(status_code=400, detail=error)

    return LabTestResponse(
        id=str(test.id),
        name=test.name,
        code=test.code,
        description=test.description,
        category=test.category,
        unit=test.unit,
        reference_range=test.reference_range,
        price=test.price,
        is_active=test.is_active,
        created_at=test.created_at.isoformat() if test.created_at else "",
        updated_at=test.updated_at.isoformat() if test.updated_at else None
    )


@router.get("/tests/{test_id}", response_model=LabTestResponse)
async def get_lab_test(
    test_id: str,
    current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
    db: Session = Depends(get_db)
):
    test = LabService.get_lab_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    return LabTestResponse(
        id=str(test.id),
        name=test.name,
        code=test.code,
        description=test.description,
        category=test.category,
        unit=test.unit,
        reference_range=test.reference_range,
        price=test.price,
        is_active=test.is_active,
        created_at=test.created_at.isoformat() if test.created_at else "",
        updated_at=test.updated_at.isoformat() if test.updated_at else None
    )


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

    updated_test = LabService.update_lab_test(test, data.dict(exclude_unset=True))

    return LabTestResponse(
        id=str(updated_test.id),
        name=updated_test.name,
        code=updated_test.code,
        description=updated_test.description,
        category=updated_test.category,
        unit=updated_test.unit,
        reference_range=updated_test.reference_range,
        price=updated_test.price,
        is_active=updated_test.is_active,
        created_at=updated_test.created_at.isoformat() if updated_test.created_at else "",
        updated_at=updated_test.updated_at.isoformat() if updated_test.updated_at else None
    )


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
            raise HTTPException(status_code=404, detail="Patient not found")
        orders = LabService.get_lab_orders_by_patient(patient_id, facility_slug)
    elif status:
        orders = LabService.get_lab_orders_by_status(status, facility_slug)
    else:
        raise HTTPException(status_code=400, detail="Please provide patient_id or status filter")

    return [
        LabOrderResponse(
            id=str(o.id),
            patient_id=str(o.patient_id),
            test_id=str(o.test_id),
            ordered_by=str(o.ordered_by),
            status=o.status,
            priority=o.priority,
            notes=o.notes,
            completed_at=o.completed_at.isoformat() if o.completed_at else None,
            facility_slug=o.facility_slug,
            created_at=o.created_at.isoformat() if o.created_at else "",
            updated_at=o.updated_at.isoformat() if o.updated_at else None
        ) for o in orders
    ]


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
    data: LabOrderCreate,
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
    db: Session = Depends(get_db)
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    payload = data.dict()
    payload['facility_slug'] = facility_slug

    order = LabService.create_lab_order(payload, current_user.id)

    return LabOrderResponse(
        id=str(order.id),
        patient_id=str(order.patient_id),
        test_id=str(order.test_id),
        ordered_by=str(order.ordered_by),
        status=order.status,
        priority=order.priority,
        notes=order.notes,
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
        facility_slug=order.facility_slug,
        created_at=order.created_at.isoformat() if order.created_at else "",
        updated_at=order.updated_at.isoformat() if order.updated_at else None
    )


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

    return LabOrderResponse(
        id=str(order.id),
        patient_id=str(order.patient_id),
        test_id=str(order.test_id),
        ordered_by=str(order.ordered_by),
        status=order.status,
        priority=order.priority,
        notes=order.notes,
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
        facility_slug=order.facility_slug,
        created_at=order.created_at.isoformat() if order.created_at else "",
        updated_at=order.updated_at.isoformat() if order.updated_at else None
    )


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

    updated_order = LabService.update_lab_order_status(order, data.status)

    return LabOrderResponse(
        id=str(updated_order.id),
        patient_id=str(updated_order.patient_id),
        test_id=str(updated_order.test_id),
        ordered_by=str(updated_order.ordered_by),
        status=updated_order.status,
        priority=updated_order.priority,
        notes=updated_order.notes,
        completed_at=updated_order.completed_at.isoformat() if updated_order.completed_at else None,
        facility_slug=updated_order.facility_slug,
        created_at=updated_order.created_at.isoformat() if updated_order.created_at else "",
        updated_at=updated_order.updated_at.isoformat() if updated_order.updated_at else None
    )


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

    return LabResultResponse(
        id=str(result.id),
        order_id=str(result.order_id),
        entered_by=str(result.entered_by) if result.entered_by else None,
        value=result.value,
        is_abnormal=result.is_abnormal,
        notes=result.notes,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else None
    )


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

    result = LabService.create_lab_result(order_id, data.dict())

    return LabResultResponse(
        id=str(result.id),
        order_id=str(result.order_id),
        entered_by=str(result.entered_by) if result.entered_by else None,
        value=result.value,
        is_abnormal=result.is_abnormal,
        notes=result.notes,
        created_at=result.created_at.isoformat() if result.created_at else "",
        updated_at=result.updated_at.isoformat() if result.updated_at else None
    )
