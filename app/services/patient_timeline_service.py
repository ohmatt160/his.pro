from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db_session
from app.models.appointment import Appointment
from app.models.billing import Invoice, Payment
from app.models.lab import LabOrder
from app.models.medical_record import MedicalRecord
from app.models.order_workflow import OrderWorkflowEvent
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.models.pharmacy import Prescription, PrescriptionItem
from app.models.radiology import Radiology
from app.models.ward import WardAdmission


def _money(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def _event(
    *,
    event_id: str,
    event_type: str,
    module: str,
    title: str,
    occurred_at: datetime | None,
    description: str = "",
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "event_type": event_type,
        "module": module,
        "title": title,
        "description": description,
        "status": status,
        "occurred_at": occurred_at.isoformat() if occurred_at else "",
        "metadata": metadata or {},
    }


class PatientTimelineService:
    @staticmethod
    def build_patient_timeline(patient: Patient, facility_slug: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = [
            _event(
                event_id=f"patient-{patient.id}",
                event_type="patient_registered",
                module="reception",
                title="Patient registered",
                description=f"{patient.full_name} was registered in the patient registry.",
                occurred_at=patient.created_at,
                status="ACTIVE" if patient.is_active else "INACTIVE",
                metadata={"patient_id": patient.id},
            )
        ]

        appointments = (
            db_session.query(Appointment)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for appointment in appointments:
            events.append(
                _event(
                    event_id=f"appointment-{appointment.id}",
                    event_type="appointment",
                    module="reception",
                    title="Appointment scheduled",
                    description=appointment.reason or "Appointment created.",
                    occurred_at=appointment.appointment_date or appointment.created_at,
                    status=appointment.status,
                    metadata={
                        "appointment_id": appointment.id,
                        "doctor_id": appointment.doctor_id,
                        "duration_minutes": appointment.duration_minutes,
                    },
                )
            )

        records = (
            db_session.query(MedicalRecord)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for record in records:
            diagnoses = record.diagnosis or []
            events.append(
                _event(
                    event_id=f"medical-record-{record.id}",
                    event_type="medical_record",
                    module="records",
                    title=record.chief_complaint or "Clinical record created",
                    description=", ".join(diagnoses) if diagnoses else record.treatment_plan or record.notes or "",
                    occurred_at=record.created_at,
                    status="RECORDED",
                    metadata={
                        "record_id": record.id,
                        "appointment_id": record.appointment_id,
                        "follow_up_date": record.follow_up_date.isoformat() if record.follow_up_date else None,
                    },
                )
            )

        lab_orders = (
            db_session.query(LabOrder)
            .options(joinedload(LabOrder.test), selectinload(LabOrder.results))
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for order in lab_orders:
            test_name = order.test.name if order.test else "Lab test"
            events.append(
                _event(
                    event_id=f"lab-order-{order.id}",
                    event_type="lab_order",
                    module="lab",
                    title=f"Lab order: {test_name}",
                    description=order.notes or f"Priority: {order.priority}",
                    occurred_at=order.order_date or order.created_at,
                    status=order.status,
                    metadata={"order_id": order.id, "test_id": order.test_id, "priority": order.priority},
                )
            )
            for result in order.results:
                events.append(
                    _event(
                        event_id=f"lab-result-{result.id}",
                        event_type="lab_result",
                        module="lab",
                        title=f"Lab result: {test_name}",
                        description=result.notes or f"Value: {result.value or 'Recorded'}",
                        occurred_at=result.result_date or result.created_at,
                        status="ABNORMAL" if result.is_abnormal else "NORMAL",
                        metadata={"order_id": order.id, "result_id": result.id, "value": result.value},
                    )
                )

        radiology_orders = (
            db_session.query(Radiology)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for order in radiology_orders:
            events.append(
                _event(
                    event_id=f"radiology-{order.id}",
                    event_type="radiology_order",
                    module="radiology",
                    title=f"{order.modality} requested",
                    description=order.body_part,
                    occurred_at=order.request_date or order.created_at,
                    status=order.status,
                    metadata={"order_id": order.id, "body_part": order.body_part},
                )
            )
            if order.report:
                events.append(
                    _event(
                        event_id=f"radiology-report-{order.id}",
                        event_type="radiology_report",
                        module="radiology",
                        title=f"{order.modality} report completed",
                        description=order.report,
                        occurred_at=order.report_date or order.updated_at,
                        status="completed",
                        metadata={"order_id": order.id},
                    )
                )

        prescriptions = (
            db_session.query(Prescription)
            .options(
                selectinload(Prescription.items).joinedload(PrescriptionItem.medication)
            )
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for prescription in prescriptions:
            medication_names = [
                item.medication.name
                for item in prescription.items
                if item.medication
            ]
            events.append(
                _event(
                    event_id=f"prescription-{prescription.id}",
                    event_type="prescription",
                    module="pharmacy",
                    title="Prescription created",
                    description=", ".join(medication_names) or prescription.notes or "",
                    occurred_at=prescription.prescription_date or prescription.created_at,
                    status=prescription.status,
                    metadata={"prescription_id": prescription.id, "items": len(prescription.items)},
                )
            )
            if prescription.dispensed_date:
                events.append(
                    _event(
                        event_id=f"dispensed-{prescription.id}",
                        event_type="prescription_dispensed",
                        module="pharmacy",
                        title="Prescription dispensed",
                        description=", ".join(medication_names) or "Medication dispensed.",
                        occurred_at=prescription.dispensed_date,
                        status="DISPENSED",
                        metadata={"prescription_id": prescription.id},
                    )
                )

        invoices = (
            db_session.query(Invoice)
            .options(selectinload(Invoice.payments))
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for invoice in invoices:
            events.append(
                _event(
                    event_id=f"invoice-{invoice.id}",
                    event_type="invoice",
                    module="billing",
                    title=f"Invoice {invoice.invoice_number}",
                    description=invoice.notes or f"Total {_money(invoice.total):,.2f}",
                    occurred_at=invoice.invoice_date or invoice.created_at,
                    status=invoice.status,
                    metadata={"invoice_id": invoice.id, "total": _money(invoice.total)},
                )
            )
            for payment in invoice.payments:
                events.append(
                    _event(
                        event_id=f"payment-{payment.id}",
                        event_type="payment",
                        module="billing",
                        title="Payment received",
                        description=f"{payment.payment_method or 'Payment'} {_money(payment.amount):,.2f}",
                        occurred_at=payment.payment_date or payment.created_at,
                        status="PAID",
                        metadata={
                            "invoice_id": invoice.id,
                            "payment_id": payment.id,
                            "amount": _money(payment.amount),
                            "reference": payment.reference_number,
                            "has_receipt": bool(payment.receipt_filename),
                            "receipt_url": f"/billing/payments/{payment.id}/receipt" if payment.receipt_filename else None,
                        },
                    )
                )

        admissions = (
            db_session.query(WardAdmission)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for admission in admissions:
            events.append(
                _event(
                    event_id=f"admission-{admission.id}",
                    event_type="ward_admission",
                    module="nursing",
                    title=f"Admitted to {admission.ward_name}",
                    description=admission.reason or "Ward admission created.",
                    occurred_at=admission.admitted_at or admission.created_at,
                    status=admission.status,
                    metadata={"admission_id": admission.id, "acuity": admission.acuity},
                )
            )
            if admission.discharged_at:
                events.append(
                    _event(
                        event_id=f"discharge-{admission.id}",
                        event_type="ward_discharge",
                        module="nursing",
                        title=f"Discharged from {admission.ward_name}",
                        description=admission.reason or "",
                        occurred_at=admission.discharged_at,
                        status="DISCHARGED",
                        metadata={"admission_id": admission.id},
                    )
                )

        workflow_events = (
            db_session.query(OrderWorkflowEvent)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for workflow in workflow_events:
            events.append(
                _event(
                    event_id=f"workflow-{workflow.id}",
                    event_type=f"workflow_{workflow.event_type}",
                    module="workflow",
                    title=workflow.title,
                    description=workflow.message or "",
                    occurred_at=workflow.occurred_at or workflow.created_at,
                    status=workflow.status,
                    metadata={
                        "workflow_event_id": workflow.id,
                        "order_type": workflow.order_type,
                        "order_id": workflow.order_id,
                        "target_role": workflow.target_role,
                        **(workflow.metadata_json or {}),
                    },
                )
            )

        notifications = (
            db_session.query(PatientNotification)
            .filter_by(patient_id=patient.id, facility_slug=facility_slug)
            .all()
        )
        for notification in notifications:
            events.append(
                _event(
                    event_id=f"patient-notification-{notification.id}",
                    event_type="patient_notification",
                    module="notifications",
                    title=notification.title,
                    description=notification.message,
                    occurred_at=notification.created_at,
                    status=notification.status,
                    metadata={
                        "notification_id": notification.id,
                        "notification_type": notification.notification_type,
                        "channel": notification.channel,
                        "source_type": notification.source_type,
                        "source_id": notification.source_id,
                        **(notification.metadata_json or {}),
                    },
                )
            )

        return sorted(
            events,
            key=lambda event: event["occurred_at"] or "",
            reverse=True,
        )
