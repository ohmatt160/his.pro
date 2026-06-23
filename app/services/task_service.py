from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db_session
from app.models.appointment import Appointment
from app.models.billing import Invoice
from app.models.inventory import Inventory
from app.models.lab import LabOrder
from app.models.medical_record import MedicalRecord
from app.models.patient_queue import PatientQueue
from app.models.pharmacy import Prescription
from app.models.radiology import Radiology
from app.models.ward import WardAdmission


ROLE_ALIASES = {
    "ADMIN": "ADMIN",
    "DOCTOR": "DOCTOR",
    "NURSE": "NURSE",
    "LAB": "LAB_TECH",
    "LAB_TECH": "LAB_TECH",
    "PHARMACIST": "PHARMACIST",
    "RECEPTION": "RECEPTIONIST",
    "RECEPTIONIST": "RECEPTIONIST",
}


def normalize_task_role(role: str | None) -> str:
    return ROLE_ALIASES.get((role or "").upper(), role or "")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _patient_name(source: Any) -> str | None:
    patient = getattr(source, "patient", None)
    return patient.full_name if patient else None


def _task(
    *,
    task_id: str,
    title: str,
    description: str,
    role: str,
    module: str,
    source_type: str,
    source_id: str,
    action_path: str,
    priority: str = "normal",
    status: str = "open",
    patient_id: str | None = None,
    patient_name: str | None = None,
    due_at: datetime | None = None,
    created_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "description": description,
        "role": role,
        "module": module,
        "priority": priority,
        "status": status,
        "source_type": source_type,
        "source_id": source_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "action_path": action_path,
        "due_at": _iso(due_at),
        "created_at": _iso(created_at) or datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }


class TaskService:
    @staticmethod
    def get_tasks_for_role(
        facility_slug: str,
        role: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        role = normalize_task_role(role)
        if role == "ADMIN":
            tasks: list[dict[str, Any]] = []
            for staff_role in ["DOCTOR", "NURSE", "LAB_TECH", "PHARMACIST", "RECEPTIONIST"]:
                tasks.extend(TaskService.get_tasks_for_role(facility_slug, staff_role, limit=20))
            return TaskService._sort_tasks(tasks)[:limit]

        builders = {
            "DOCTOR": TaskService._doctor_tasks,
            "NURSE": TaskService._nurse_tasks,
            "LAB_TECH": TaskService._lab_tasks,
            "PHARMACIST": TaskService._pharmacy_tasks,
            "RECEPTIONIST": TaskService._reception_tasks,
        }
        builder = builders.get(role)
        if not builder:
            return []
        return TaskService._sort_tasks(builder(facility_slug))[:limit]

    @staticmethod
    def _sort_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        return sorted(
            tasks,
            key=lambda task: (
                priority_rank.get(task["priority"], 2),
                task["due_at"] or task["created_at"],
            ),
        )

    @staticmethod
    def _doctor_tasks(facility_slug: str) -> list[dict[str, Any]]:
        tasks = []
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        appointments = (
            db_session.query(Appointment)
            .options(joinedload(Appointment.patient))
            .filter(
                Appointment.facility_slug == facility_slug,
                Appointment.appointment_date >= today_start,
                Appointment.appointment_date < today_end,
                Appointment.status.in_(["SCHEDULED", "CONFIRMED", "IN_PROGRESS"]),
            )
            .limit(25)
            .all()
        )
        for appointment in appointments:
            tasks.append(
                _task(
                    task_id=f"doctor-appointment-{appointment.id}",
                    title="Review appointment",
                    description=appointment.reason or "Patient appointment is ready for review.",
                    role="DOCTOR",
                    module="consultations",
                    source_type="appointment",
                    source_id=appointment.id,
                    patient_id=appointment.patient_id,
                    patient_name=_patient_name(appointment),
                    action_path="consultations",
                    priority="high" if appointment.appointment_date <= now else "normal",
                    due_at=appointment.appointment_date,
                    created_at=appointment.created_at,
                )
            )

        incomplete_records = (
            db_session.query(MedicalRecord)
            .options(joinedload(MedicalRecord.patient))
            .filter(
                MedicalRecord.facility_slug == facility_slug,
                or_(MedicalRecord.diagnosis == None, MedicalRecord.treatment_plan == None),
            )
            .limit(25)
            .all()
        )
        for record in incomplete_records:
            tasks.append(
                _task(
                    task_id=f"doctor-record-{record.id}",
                    title="Complete consultation note",
                    description=record.chief_complaint or "Clinical note needs diagnosis or treatment plan.",
                    role="DOCTOR",
                    module="consultations",
                    source_type="medical_record",
                    source_id=record.id,
                    patient_id=record.patient_id,
                    patient_name=_patient_name(record),
                    action_path="consultations",
                    priority="normal",
                    created_at=record.created_at,
                )
            )

        completed_lab_orders = (
            db_session.query(LabOrder)
            .options(joinedload(LabOrder.test))
            .filter(
                LabOrder.facility_slug == facility_slug,
                LabOrder.status == "COMPLETED",
            )
            .limit(25)
            .all()
        )
        for order in completed_lab_orders:
            tasks.append(
                _task(
                    task_id=f"doctor-lab-result-{order.id}",
                    title="Review lab result",
                    description=order.test.name if order.test else "Lab result is ready.",
                    role="DOCTOR",
                    module="lab",
                    source_type="lab_order",
                    source_id=order.id,
                    patient_id=order.patient_id,
                    patient_name=_patient_name(order),
                    action_path="laboratory",
                    priority="high" if order.priority in {"URGENT", "EMERGENCY"} else "normal",
                    created_at=order.completed_date or order.created_at,
                )
            )

        completed_radiology = (
            db_session.query(Radiology)
            .options(joinedload(Radiology.patient))
            .filter_by(facility_slug=facility_slug, status="completed")
            .limit(25)
            .all()
        )
        for order in completed_radiology:
            tasks.append(
                _task(
                    task_id=f"doctor-radiology-{order.id}",
                    title="Review radiology report",
                    description=f"{order.modality} - {order.body_part}",
                    role="DOCTOR",
                    module="radiology",
                    source_type="radiology_order",
                    source_id=order.id,
                    patient_id=order.patient_id,
                    patient_name=_patient_name(order),
                    action_path="radiology",
                    priority="normal",
                    created_at=order.report_date or order.updated_at,
                )
            )
        return tasks

    @staticmethod
    def _nurse_tasks(facility_slug: str) -> list[dict[str, Any]]:
        tasks = []
        admissions = (
            db_session.query(WardAdmission)
            .options(joinedload(WardAdmission.patient))
            .filter_by(facility_slug=facility_slug, status="ACTIVE")
            .limit(50)
            .all()
        )
        for admission in admissions:
            tasks.append(
                _task(
                    task_id=f"nurse-admission-{admission.id}",
                    title="Ward patient review",
                    description=admission.reason or f"{admission.ward_name} observation due.",
                    role="NURSE",
                    module="nursing",
                    source_type="ward_admission",
                    source_id=admission.id,
                    patient_id=admission.patient_id,
                    patient_name=_patient_name(admission),
                    action_path="wards",
                    priority="urgent" if admission.acuity == "urgent" else "normal",
                    created_at=admission.admitted_at or admission.created_at,
                    metadata={"ward_name": admission.ward_name, "acuity": admission.acuity},
                )
            )
        return tasks

    @staticmethod
    def _lab_tasks(facility_slug: str) -> list[dict[str, Any]]:
        tasks = []
        orders = (
            db_session.query(LabOrder)
            .options(joinedload(LabOrder.test))
            .filter(
                LabOrder.facility_slug == facility_slug,
                LabOrder.status.in_(["PENDING", "COLLECTED", "IN_PROGRESS"]),
            )
            .limit(50)
            .all()
        )
        for order in orders:
            status_action = {
                "PENDING": "Collect sample",
                "COLLECTED": "Process sample",
                "IN_PROGRESS": "Release result",
            }.get(order.status, "Process lab order")
            tasks.append(
                _task(
                    task_id=f"lab-order-{order.id}",
                    title=status_action,
                    description=order.test.name if order.test else "Lab order pending.",
                    role="LAB_TECH",
                    module="lab",
                    source_type="lab_order",
                    source_id=order.id,
                    patient_id=order.patient_id,
                    patient_name=_patient_name(order),
                    action_path="laboratory",
                    priority="urgent" if order.priority in {"URGENT", "EMERGENCY"} else "normal",
                    created_at=order.order_date or order.created_at,
                    metadata={"status": order.status, "priority": order.priority},
                )
            )
        return tasks

    @staticmethod
    def _pharmacy_tasks(facility_slug: str) -> list[dict[str, Any]]:
        tasks = []
        prescriptions = (
            db_session.query(Prescription)
            .options(selectinload(Prescription.items))
            .filter_by(facility_slug=facility_slug, status="PENDING")
            .limit(50)
            .all()
        )
        for prescription in prescriptions:
            tasks.append(
                _task(
                    task_id=f"pharmacy-prescription-{prescription.id}",
                    title="Dispense prescription",
                    description=prescription.notes or f"{len(prescription.items)} item(s) pending.",
                    role="PHARMACIST",
                    module="pharmacy",
                    source_type="prescription",
                    source_id=prescription.id,
                    patient_id=prescription.patient_id,
                    patient_name=_patient_name(prescription),
                    action_path="pharmacy",
                    priority="high",
                    created_at=prescription.prescription_date or prescription.created_at,
                )
            )

        low_stock = (
            db_session.query(Inventory)
            .filter(
                Inventory.facility_slug == facility_slug,
                Inventory.is_active == True,
                Inventory.current_stock <= Inventory.reorder_level,
            )
            .limit(50)
            .all()
        )
        for item in low_stock:
            tasks.append(
                _task(
                    task_id=f"pharmacy-low-stock-{item.id}",
                    title="Review low stock",
                    description=f"{item.name} is at {item.current_stock} {item.unit}.",
                    role="PHARMACIST",
                    module="inventory",
                    source_type="inventory_item",
                    source_id=item.id,
                    action_path="inventory",
                    priority="high",
                    created_at=item.updated_at or item.created_at,
                    metadata={"sku": item.sku, "reorder_level": item.reorder_level},
                )
            )
        return tasks

    @staticmethod
    def _reception_tasks(facility_slug: str) -> list[dict[str, Any]]:
        tasks = []
        queue_entries = (
            db_session.query(PatientQueue)
            .options(joinedload(PatientQueue.patient))
            .filter(
                PatientQueue.facility_slug == facility_slug,
                PatientQueue.status.in_(["waiting", "in_progress"]),
            )
            .limit(50)
            .all()
        )
        for entry in queue_entries:
            tasks.append(
                _task(
                    task_id=f"reception-queue-{entry.id}",
                    title="Manage patient queue",
                    description=f"{entry.department} queue #{entry.queue_number}",
                    role="RECEPTIONIST",
                    module="reception",
                    source_type="patient_queue",
                    source_id=entry.id,
                    patient_id=entry.patient_id,
                    patient_name=_patient_name(entry),
                    action_path="queue",
                    priority="urgent" if entry.priority == "urgent" else "normal",
                    created_at=entry.checked_in_at or entry.created_at,
                    metadata={"department": entry.department, "queue_number": entry.queue_number},
                )
            )

        invoices = (
            db_session.query(Invoice)
            .filter(
                Invoice.facility_slug == facility_slug,
                Invoice.status.in_(["PENDING", "PARTIAL"]),
            )
            .limit(50)
            .all()
        )
        for invoice in invoices:
            tasks.append(
                _task(
                    task_id=f"reception-invoice-{invoice.id}",
                    title="Confirm patient payment",
                    description=f"Invoice {invoice.invoice_number} is {invoice.status.lower()}.",
                    role="RECEPTIONIST",
                    module="billing",
                    source_type="invoice",
                    source_id=invoice.id,
                    patient_id=invoice.patient_id,
                    patient_name=_patient_name(invoice),
                    action_path="billing",
                    priority="normal",
                    due_at=datetime.combine(invoice.due_date, datetime.min.time()) if invoice.due_date else None,
                    created_at=invoice.invoice_date or invoice.created_at,
                )
            )
        return tasks
