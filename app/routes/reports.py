from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_

from app.extensions import db_session
from app.models.alert import Alert
from app.models.appointment import Appointment
from app.models.billing import Invoice, Payment
from app.models.inventory import Inventory
from app.models.lab import LabOrder
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.patient_queue import PatientQueue
from app.models.radiology import Radiology
from app.models.user import User
from app.models.ward import WardAdmission
from app.schemas.reports import (
    FacilityReportSummary,
    InventoryReport,
    ReportSection,
    RevenueReport,
)
from app.utils.dependencies import role_required

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_date(value: Optional[str], fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")


def _date_bounds(date_from: Optional[str], date_to: Optional[str]) -> tuple[datetime, datetime]:
    today = datetime.utcnow().date()
    start_date = _parse_date(date_from, today - timedelta(days=30))
    end_date = _parse_date(date_to, today)
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="date_from cannot be after date_to")
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max)


def _money(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _status_section(model, facility_slug: str, status_column, created_column, start: datetime, end: datetime) -> ReportSection:
    rows = (
        db_session.query(status_column, func.count(model.id))
        .filter(model.facility_slug == facility_slug, created_column >= start, created_column <= end)
        .group_by(status_column)
        .all()
    )
    by_status = {str(status or "unknown"): int(count) for status, count in rows}
    return ReportSection(total=sum(by_status.values()), by_status=by_status)


@router.get("/summary", response_model=FacilityReportSummary)
async def get_report_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST")),
):
    facility_slug = current_user.facility_slug
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    start, end = _date_bounds(date_from, date_to)

    patients_total = db_session.query(Patient).filter(
        Patient.facility_slug == facility_slug,
        Patient.created_at >= start,
        Patient.created_at <= end,
    ).count()

    consultations_total = db_session.query(MedicalRecord).filter(
        MedicalRecord.facility_slug == facility_slug,
        MedicalRecord.created_at >= start,
        MedicalRecord.created_at <= end,
    ).count()

    invoices = db_session.query(Invoice).filter(
        Invoice.facility_slug == facility_slug,
        Invoice.invoice_date >= start,
        Invoice.invoice_date <= end,
    )
    invoice_count = invoices.count()
    outstanding_invoice_count = invoices.filter(Invoice.status.in_(["PENDING", "PARTIAL"])).count()
    invoiced_total = _money(invoices.with_entities(func.coalesce(func.sum(Invoice.total), 0)).scalar())

    payments_total = _money(
        db_session.query(func.coalesce(func.sum(Payment.amount), 0))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(
            Invoice.facility_slug == facility_slug,
            Payment.payment_date >= start,
            Payment.payment_date <= end,
        )
        .scalar()
    )

    active_items = db_session.query(Inventory).filter_by(
        facility_slug=facility_slug,
        is_active=True,
    ).count()
    low_stock_items = db_session.query(Inventory).filter(
        Inventory.facility_slug == facility_slug,
        Inventory.is_active == True,
        Inventory.current_stock <= Inventory.reorder_level,
    ).count()
    stock_value = _money(
        db_session.query(func.coalesce(func.sum(Inventory.current_stock * Inventory.unit_cost), 0))
        .filter(Inventory.facility_slug == facility_slug, Inventory.is_active == True)
        .scalar()
    )

    active_alerts = db_session.query(Alert).filter(
        Alert.facility_slug == facility_slug,
        Alert.is_read == False,
    ).filter(or_(Alert.expires_at == None, Alert.expires_at > datetime.utcnow())).count()

    return FacilityReportSummary(
        facility_slug=facility_slug,
        date_from=start.date().isoformat(),
        date_to=end.date().isoformat(),
        patients=ReportSection(total=patients_total, by_status={"active": patients_total}),
        appointments=_status_section(Appointment, facility_slug, Appointment.status, Appointment.created_at, start, end),
        consultations=ReportSection(total=consultations_total, by_status={"records": consultations_total}),
        admissions=_status_section(WardAdmission, facility_slug, WardAdmission.status, WardAdmission.created_at, start, end),
        queue=_status_section(PatientQueue, facility_slug, PatientQueue.status, PatientQueue.created_at, start, end),
        laboratory=_status_section(LabOrder, facility_slug, LabOrder.status, LabOrder.created_at, start, end),
        radiology=_status_section(Radiology, facility_slug, Radiology.status, Radiology.created_at, start, end),
        billing=RevenueReport(
            invoice_count=invoice_count,
            outstanding_invoice_count=outstanding_invoice_count,
            invoiced_total=invoiced_total,
            payments_total=payments_total,
            outstanding_total=max(invoiced_total - payments_total, 0),
        ),
        inventory=InventoryReport(
            active_items=active_items,
            low_stock_items=low_stock_items,
            stock_value=stock_value,
        ),
        alerts=ReportSection(total=active_alerts, by_status={"active": active_alerts}),
        generated_at=datetime.utcnow().isoformat(),
    )
