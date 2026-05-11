"""
Laboratory Routes - FastAPI Version
Converted from Flask-RESTx lab_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db
from app.utils.dependencies import get_current_user, role_required
from app.services.lab_service import LabService
from app.models.user import User
from app.models.patient import Patient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/laboratory", tags=["laboratory"])


# Pydantic Models
class LabTestCreate(BaseModel):
    name: str = Field(...)
    code: str = Field(...)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    unit: Optional[str] = Field(None)
    reference_range: Optional[str] = Field(None)
    price: Optional[float] = Field(None)


class LabTestUpdate(BaseModel):
    name: Optional[str] = Field(None)
    code: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    unit: Optional[str] = Field(None)
    reference_range: Optional[str] = Field(None)
    price: Optional[float] = Field(None)


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
    priority: Optional[str] = Field("routine")
    notes: Optional[str] = Field(None)
    order_date: Optional[str] = Field(None)


class LabOrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING|COLLECTED|IN_PROGRESS|COMPLETED|CANCELLED)$")


class LabOrderResponse(BaseModel):
    id: str
    patient_id: str
    test_id: str
    facility_slug: str
    status: str
    priority: str
    notes: Optional[str]
    order_date: str
    created_at: str
    updated_at: Optional[str]


class LabResultCreate(BaseModel):
    value: Optional[str] = Field(None)
    is_abnormal: Optional[bool] = Field(None)
    notes: Optional[str] = Field(None)


class LabResultResponse(BaseModel):
    id: str
    order_id: str
    value: Optional[str]
    is_abnormal: Optional[bool]
    notes: Optional[str]
    created_at: str
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    message: str


# ==================== Lab Tests ====================

@router.get("/tests", response_model=List[LabTestResponse])
async def list_lab_tests(
        active_only: bool = Query(True),
        current_user: User = Depends(role_required('ADMIN', 'LAB_TECH')),
        db: Session = Depends(get_db)
):
    """Get all lab tests"""
    tests = LabService.get_all_lab_tests(active_only=active_only)
    return tests


@router.post("/tests", response_model=LabTestResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_test(
        data: LabTestCreate,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Create a new lab test"""
    test, error = LabService.create_lab_test(data.dict())

    if error:
        raise HTTPException(status_code=400, detail=error)

    return test


@router.get("/tests/{test_id}", response_model=LabTestResponse)
async def get_lab_test(
        test_id: str,
        current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
        db: Session = Depends(get_db)
):
    """Get lab test by ID"""
    test = LabService.get_lab_test_by_id(test_id)

    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    return test


@router.put("/tests/{test_id}", response_model=LabTestResponse)
async def update_lab_test(
        test_id: str,
        data: LabTestUpdate,
        current_user: User = Depends(role_required('ADMIN')),
        db: Session = Depends(get_db)
):
    """Update lab test"""
    test = LabService.get_lab_test_by_id(test_id)

    if not test:
        raise HTTPException(status_code=404, detail="Lab test not found")

    updated_test = LabService.update_lab_test(test, data.dict(exclude_unset=True))

    return updated_test


# ==================== Lab Orders ====================

@router.get("/orders", response_model=List[LabOrderResponse])
async def list_lab_orders(
        patient_id: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
        db: Session = Depends(get_db)
):
    """Get lab orders"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    if patient_id:
        patient = db.query(Patient).filter_by(id=patient_id, facility_slug=facility_slug).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        orders = LabService.get_lab_orders_by_patient(patient_id, facility_slug)
    elif status:
        orders = LabService.get_lab_orders_by_status(status, facility_slug)
    else:
        raise HTTPException(status_code=400, detail="Please provide patient_id or status filter")

    return orders


@router.post("/orders", response_model=LabOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_order(
        data: LabOrderCreate,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE')),
        db: Session = Depends(get_db)
):
    """Create a new lab order"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    # Verify patient belongs to facility
    patient = db.query(Patient).filter_by(id=data.patient_id, facility_slug=facility_slug).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    order_data = data.dict()
    order_data['facility_slug'] = facility_slug

    order = LabService.create_lab_order(order_data, str(current_user.id))

    return order


@router.get("/orders/{order_id}", response_model=LabOrderResponse)
async def get_lab_order(
        order_id: str,
        current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')),
        db: Session = Depends(get_db)
):
    """Get lab order by ID"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    return order


@router.put("/orders/{order_id}", response_model=LabOrderResponse)
async def update_lab_order_status(
        order_id: str,
        data: LabOrderStatusUpdate,
        current_user: User = Depends(role_required('ADMIN', 'LAB_TECH')),
        db: Session = Depends(get_db)
):
    """Update lab order status"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    updated_order = LabService.update_lab_order_status(order, data.status)

    return updated_order


# ==================== Lab Results ====================

@router.get("/results/{order_id}", response_model=LabResultResponse)
async def get_lab_result(
        order_id: str,
        current_user: User = Depends(role_required('ADMIN', 'LAB_TECH', 'DOCTOR')),
        db: Session = Depends(get_db)
):
    """Get lab result for an order"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = LabService.get_lab_order_by_id(order_id)
    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab result not found")

    result = LabService.get_result_by_order(order_id)

    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")

    return result


@router.post("/results/{order_id}", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
        order_id: str,
        data: LabResultCreate,
        current_user: User = Depends(role_required('ADMIN', 'LAB_TECH')),
        db: Session = Depends(get_db)
):
    """Create or update lab result"""
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    order = LabService.get_lab_order_by_id(order_id)

    if not order or order.facility_slug != facility_slug:
        raise HTTPException(status_code=404, detail="Lab order not found")

    if order.status == 'COMPLETED':
        raise HTTPException(status_code=400, detail="Lab order already completed")

    result = LabService.create_lab_result(order_id, data.dict())

    return result