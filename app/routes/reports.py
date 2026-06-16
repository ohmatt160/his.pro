from datetime import date, datetime, time, timedelta
from decimal import Decimal
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db_session
from app.models.alert import Alert
from app.models.appointment import Appointment
from app.models.billing import Invoice, Payment
from app.models.inventory import Inventory
from app.models.lab import LabOrder
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.patient_queue import PatientQueue
from app.models.pharmacy import Prescription
from app.models.radiology import Radiology
from app.models.user import User
from app.models.ward import WardAdmission
from app.schemas.reports import (
    DepartmentActivityReport,
    DepartmentActivityRow,
    FacilityReportSummary,
    InventoryDetailItem,
    InventoryDetailReport,
    InventoryReport,
    OperationsReport,
    ReportMetricRow,
    ReportSection,
    RevenueDetailReport,
    RevenueReport,
)
from app.services.task_service import TaskService
from app.utils.dependencies import role_required

logger = logging.getLogger(__name__)
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


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _status_rows(model, facility_slug: str, status_column, created_column, start: datetime, end: datetime) -> dict[str, int]:
    rows = (
        db_session.query(status_column, func.count(model.id))
        .filter(model.facility_slug == facility_slug, created_column >= start, created_column <= end)
        .group_by(status_column)
        .all()
    )
    return {str(status or "unknown"): int(count) for status, count in rows}


def _department_row(
    *,
    department: str,
    module: str,
    by_status: dict[str, int],
    completed_statuses: set[str],
) -> DepartmentActivityRow:
    total = sum(by_status.values())
    completed = sum(count for status, count in by_status.items() if status in completed_statuses)
    return DepartmentActivityRow(
        department=department,
        module=module,
        total=total,
        completed=completed,
        pending=max(total - completed, 0),
        by_status=by_status,
    )


def _empty_report_section() -> ReportSection:
    return ReportSection(total=0, by_status={})


def _empty_revenue_report() -> RevenueReport:
    return RevenueReport(
        invoice_count=0,
        outstanding_invoice_count=0,
        invoiced_total=0,
        payments_total=0,
        outstanding_total=0,
    )


def _empty_inventory_report() -> InventoryReport:
    return InventoryReport(active_items=0, low_stock_items=0, stock_value=0)


def _empty_summary(facility_slug: str, start: datetime, end: datetime) -> FacilityReportSummary:
    return FacilityReportSummary(
        facility_slug=facility_slug,
        date_from=start.date().isoformat(),
        date_to=end.date().isoformat(),
        patients=_empty_report_section(),
        appointments=_empty_report_section(),
        consultations=_empty_report_section(),
        admissions=_empty_report_section(),
        queue=_empty_report_section(),
        laboratory=_empty_report_section(),
        radiology=_empty_report_section(),
        billing=_empty_revenue_report(),
        inventory=_empty_inventory_report(),
        alerts=_empty_report_section(),
        generated_at=datetime.utcnow().isoformat(),
    )


@router.get("/summary", response_model=FacilityReportSummary)
async def get_report_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH")),
):
    facility_slug = _require_facility(current_user)

    start, end = _date_bounds(date_from, date_to)
    try:
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
    except SQLAlchemyError:
        logger.warning("Returning empty report summary for %s after database read failed", facility_slug, exc_info=True)
        db_session.rollback()
        return _empty_summary(facility_slug, start, end)


@router.get("/revenue", response_model=RevenueDetailReport)
async def get_revenue_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "RECEPTIONIST")),
):
    facility_slug = _require_facility(current_user)
    start, end = _date_bounds(date_from, date_to)
    try:
        invoices_query = db_session.query(Invoice).filter(
            Invoice.facility_slug == facility_slug,
            Invoice.invoice_date >= start,
            Invoice.invoice_date <= end,
        )
        invoice_count = invoices_query.count()
        paid_invoice_count = invoices_query.filter(Invoice.status == "PAID").count()
        outstanding_invoice_count = invoices_query.filter(Invoice.status.in_(["PENDING", "PARTIAL"])).count()
        invoiced_total = _money(invoices_query.with_entities(func.coalesce(func.sum(Invoice.total), 0)).scalar())

        payments_query = (
            db_session.query(Payment)
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .filter(
                Invoice.facility_slug == facility_slug,
                Payment.payment_date >= start,
                Payment.payment_date <= end,
            )
        )
        collected_total = _money(payments_query.with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar())
        receipt_count = payments_query.filter(Payment.receipt_filename != None).count()

        method_rows = (
            payments_query.with_entities(Payment.payment_method, func.coalesce(func.sum(Payment.amount), 0), func.count(Payment.id))
            .group_by(Payment.payment_method)
            .all()
        )
        status_rows = (
            invoices_query.with_entities(Invoice.status, func.count(Invoice.id))
            .group_by(Invoice.status)
            .all()
        )
        recent_payments = payments_query.order_by(Payment.payment_date.desc()).limit(10).all()

        return RevenueDetailReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            invoice_count=invoice_count,
            paid_invoice_count=paid_invoice_count,
            outstanding_invoice_count=outstanding_invoice_count,
            invoiced_total=invoiced_total,
            collected_total=collected_total,
            outstanding_total=max(invoiced_total - collected_total, 0),
            receipt_count=receipt_count,
            payment_methods=[
                ReportMetricRow(label=str(method or "UNKNOWN"), value=_money(total), metadata={"count": int(count)})
                for method, total, count in method_rows
            ],
            invoice_statuses=[
                ReportMetricRow(label=str(status or "UNKNOWN"), value=int(count))
                for status, count in status_rows
            ],
            recent_payments=[
                ReportMetricRow(
                    label=payment.invoice.invoice_number if payment.invoice else "Payment",
                    value=_money(payment.amount),
                    metadata={
                        "method": payment.payment_method,
                        "reference": payment.reference_number,
                        "has_receipt": bool(payment.receipt_filename),
                        "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                    },
                )
                for payment in recent_payments
            ],
            generated_at=datetime.utcnow().isoformat(),
        )
    except SQLAlchemyError:
        logger.warning("Returning empty revenue report for %s after database read failed", facility_slug, exc_info=True)
        db_session.rollback()
        return RevenueDetailReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            invoice_count=0,
            paid_invoice_count=0,
            outstanding_invoice_count=0,
            invoiced_total=0,
            collected_total=0,
            outstanding_total=0,
            receipt_count=0,
            payment_methods=[],
            invoice_statuses=[],
            recent_payments=[],
            generated_at=datetime.utcnow().isoformat(),
        )


@router.get("/departments", response_model=DepartmentActivityReport)
async def get_department_activity_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH")),
):
    facility_slug = _require_facility(current_user)
    start, end = _date_bounds(date_from, date_to)
    try:
        consultation_count = db_session.query(MedicalRecord).filter(
            MedicalRecord.facility_slug == facility_slug,
            MedicalRecord.created_at >= start,
            MedicalRecord.created_at <= end,
        ).count()

        departments = [
            DepartmentActivityRow(
                department="Consultations",
                module="consultations",
                total=consultation_count,
                completed=consultation_count,
                pending=0,
                by_status={"records": consultation_count},
            ),
            _department_row(
                department="Laboratory",
                module="lab",
                by_status=_status_rows(LabOrder, facility_slug, LabOrder.status, LabOrder.created_at, start, end),
                completed_statuses={"COMPLETED"},
            ),
            _department_row(
                department="Radiology",
                module="radiology",
                by_status=_status_rows(Radiology, facility_slug, Radiology.status, Radiology.created_at, start, end),
                completed_statuses={"completed"},
            ),
            _department_row(
                department="Pharmacy",
                module="pharmacy",
                by_status=_status_rows(Prescription, facility_slug, Prescription.status, Prescription.created_at, start, end),
                completed_statuses={"DISPENSED"},
            ),
            _department_row(
                department="Wards",
                module="nursing",
                by_status=_status_rows(WardAdmission, facility_slug, WardAdmission.status, WardAdmission.created_at, start, end),
                completed_statuses={"DISCHARGED", "TRANSFERRED"},
            ),
        ]

        return DepartmentActivityReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            departments=departments,
            generated_at=datetime.utcnow().isoformat(),
        )
    except SQLAlchemyError:
        logger.warning("Returning empty department report for %s after database read failed", facility_slug, exc_info=True)
        db_session.rollback()
        return DepartmentActivityReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            departments=[],
            generated_at=datetime.utcnow().isoformat(),
        )


@router.get("/operations", response_model=OperationsReport)
async def get_operations_report(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(role_required("ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH")),
):
    facility_slug = _require_facility(current_user)
    start, end = _date_bounds(date_from, date_to)
    try:
        task_roles = ["DOCTOR", "NURSE", "LAB_TECH", "PHARMACIST", "RECEPTIONIST"]
        role_tasks = {
            role: TaskService.get_tasks_for_role(facility_slug, role, limit=100)
            for role in task_roles
        }
        all_tasks = [task for tasks in role_tasks.values() for task in tasks]

        return OperationsReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            queue=_status_section(PatientQueue, facility_slug, PatientQueue.status, PatientQueue.created_at, start, end),
            appointments=_status_section(Appointment, facility_slug, Appointment.status, Appointment.created_at, start, end),
            active_tasks_by_role=[
                ReportMetricRow(label=role, value=len(tasks))
                for role, tasks in role_tasks.items()
            ],
            high_priority_tasks=[
                ReportMetricRow(
                    label=task["title"],
                    value=1,
                    metadata={
                        "role": task["role"],
                        "module": task["module"],
                        "priority": task["priority"],
                        "patient_name": task.get("patient_name"),
                        "action_path": task["action_path"],
                    },
                )
                for task in all_tasks
                if task["priority"] in {"urgent", "high"}
            ][:20],
            generated_at=datetime.utcnow().isoformat(),
        )
    except SQLAlchemyError:
        logger.warning("Returning empty operations report for %s after database read failed", facility_slug, exc_info=True)
        db_session.rollback()
        return OperationsReport(
            facility_slug=facility_slug,
            date_from=start.date().isoformat(),
            date_to=end.date().isoformat(),
            queue=_empty_report_section(),
            appointments=_empty_report_section(),
            active_tasks_by_role=[],
            high_priority_tasks=[],
            generated_at=datetime.utcnow().isoformat(),
        )


@router.get("/inventory", response_model=InventoryDetailReport)
async def get_inventory_detail_report(
    current_user: User = Depends(role_required("ADMIN", "PHARMACIST")),
):
    facility_slug = _require_facility(current_user)
    try:
        items = db_session.query(Inventory).filter_by(facility_slug=facility_slug, is_active=True).all()
        low_stock = [item for item in items if item.current_stock <= item.reorder_level]
        stock_value = sum(_money(item.current_stock * item.unit_cost) for item in items)
        category_totals: dict[str, float] = {}
        for item in items:
            category_totals[item.category] = category_totals.get(item.category, 0) + _money(item.current_stock * item.unit_cost)

        return InventoryDetailReport(
            facility_slug=facility_slug,
            active_items=len(items),
            low_stock_items=len(low_stock),
            stock_value=stock_value,
            reorder_items=[
                InventoryDetailItem(
                    id=item.id,
                    name=item.name,
                    sku=item.sku,
                    category=item.category,
                    current_stock=item.current_stock,
                    reorder_level=item.reorder_level,
                    reorder_quantity=item.reorder_quantity,
                    unit=item.unit,
                    stock_value=_money(item.current_stock * item.unit_cost),
                    supplier_name=item.supplier.name if item.supplier else None,
                )
                for item in low_stock
            ],
            by_category=[
                ReportMetricRow(label=category, value=value)
                for category, value in sorted(category_totals.items())
            ],
            generated_at=datetime.utcnow().isoformat(),
        )
    except SQLAlchemyError:
        logger.warning("Returning empty inventory report for %s after database read failed", facility_slug, exc_info=True)
        db_session.rollback()
        return InventoryDetailReport(
            facility_slug=facility_slug,
            active_items=0,
            low_stock_items=0,
            stock_value=0,
            reorder_items=[],
            by_category=[],
            generated_at=datetime.utcnow().isoformat(),
        )
