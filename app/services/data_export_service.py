"""Tenant-scoped, portable migration exports.

Exports are generated only for a facility administrator and stream from a
temporary file. They are never retained as a shared server-side artifact.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.billing import InsuranceClaim, Invoice, InvoiceItem, Payment
from app.models.branch import Branch
from app.models.facility import Facility
from app.models.inventory import Inventory
from app.models.lab import LabOrder, LabResult, LabTest
from app.models.medical_record import ClinicalNote, MedicalRecord
from app.models.order_workflow import OrderWorkflowEvent
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.models.patient_queue import PatientQueue
from app.models.pharmacy import Medication, PharmacyInventory, Prescription, PrescriptionItem
from app.models.radiology import Radiology
from app.models.referral import Referral
from app.models.staff_chat import ChatConversation, ChatMessage
from app.models.supplier import Supplier
from app.models.user import User
from app.models.ward import WardAdmission, WardBed
from app.security.data_classification import (
    DataClassification,
    classification_for_export_entity,
    redact_secrets,
)


EXPORT_FORMAT = "hispro-migration-export"
EXPORT_VERSION = "1.0"
CHUNK_SIZE = 64 * 1024
QUERY_BATCH_SIZE = 500


@dataclass
class DataExportArchive:
    file: tempfile.SpooledTemporaryFile
    filename: str
    manifest: dict[str, Any]


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def _record(instance: Any) -> dict[str, Any]:
    data = instance.to_dict() if hasattr(instance, "to_dict") else {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }
    return redact_secrets(_json_value(data))


def _direct_query(session: Session, model: Any, facility: Facility):
    clauses = []
    columns = model.__table__.columns
    if "facility_id" in columns:
        clauses.append(model.facility_id == facility.id)
    if "facility_slug" in columns:
        clauses.append(model.facility_slug == facility.slug)
    if not clauses:
        raise ValueError(f"{model.__tablename__} is not tenant-scoped")
    return session.query(model).filter(or_(*clauses))


def _ids(query: Any, column: Any) -> list[str]:
    return [str(value) for (value,) in query.with_entities(column).all()]


def _query_for_ids(session: Session, model: Any, column: Any, values: list[str]):
    if not values:
        return ()
    return session.query(model).filter(column.in_(values))


class DataExportService:
    """Build a full, tenant-isolated, JSON-in-ZIP export."""

    @staticmethod
    def create_archive(session: Session, facility: Facility) -> DataExportArchive:
        if not facility.is_active:
            raise ValueError("Inactive facilities cannot be exported")

        archive_file = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        manifest_entities: list[dict[str, Any]] = []
        try:
            with zipfile.ZipFile(
                archive_file,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                DataExportService._write_query(
                    archive,
                    "facility",
                    [facility],
                    manifest_entities,
                )

                branches = _direct_query(session, Branch, facility)
                users = _direct_query(session, User, facility)
                patients = _direct_query(session, Patient, facility)
                appointments = _direct_query(session, Appointment, facility)
                records = _direct_query(session, MedicalRecord, facility)
                lab_tests = _direct_query(session, LabTest, facility)
                lab_orders = _direct_query(session, LabOrder, facility)
                medications = _direct_query(session, Medication, facility)
                prescriptions = _direct_query(session, Prescription, facility)
                invoices = _direct_query(session, Invoice, facility)

                direct_entities = [
                    ("branches", branches),
                    ("users", users),
                    ("patients", patients),
                    ("appointments", appointments),
                    ("medical_records", records),
                    ("lab_tests", lab_tests),
                    ("lab_orders", lab_orders),
                    ("medications", medications),
                    ("prescriptions", prescriptions),
                    ("invoices", invoices),
                    ("inventory", _direct_query(session, Inventory, facility)),
                    ("suppliers", _direct_query(session, Supplier, facility)),
                    ("radiology_orders", _direct_query(session, Radiology, facility)),
                    ("ward_beds", _direct_query(session, WardBed, facility)),
                    ("ward_admissions", _direct_query(session, WardAdmission, facility)),
                    ("patient_queues", _direct_query(session, PatientQueue, facility)),
                    ("patient_notifications", _direct_query(session, PatientNotification, facility)),
                    ("order_workflow_events", _direct_query(session, OrderWorkflowEvent, facility)),
                    ("referrals", _direct_query(session, Referral, facility)),
                    ("chat_conversations", _direct_query(session, ChatConversation, facility)),
                    ("chat_messages", _direct_query(session, ChatMessage, facility)),
                    ("alerts", _direct_query(session, Alert, facility)),
                    ("audit_logs", _direct_query(session, AuditLog, facility)),
                ]
                for entity, query in direct_entities:
                    DataExportService._write_query(archive, entity, query, manifest_entities)

                patient_ids = _ids(patients, Patient.id)
                record_ids = _ids(records, MedicalRecord.id)
                order_ids = _ids(lab_orders, LabOrder.id)
                medication_ids = _ids(medications, Medication.id)
                prescription_ids = _ids(prescriptions, Prescription.id)
                invoice_ids = _ids(invoices, Invoice.id)

                indirect_entities = [
                    ("clinical_notes", _query_for_ids(session, ClinicalNote, ClinicalNote.patient_id, patient_ids)),
                    ("lab_results", _query_for_ids(session, LabResult, LabResult.order_id, order_ids)),
                    ("pharmacy_inventory", _query_for_ids(session, PharmacyInventory, PharmacyInventory.medication_id, medication_ids)),
                    ("prescription_items", _query_for_ids(session, PrescriptionItem, PrescriptionItem.prescription_id, prescription_ids)),
                    ("invoice_items", _query_for_ids(session, InvoiceItem, InvoiceItem.invoice_id, invoice_ids)),
                    ("payments", _query_for_ids(session, Payment, Payment.invoice_id, invoice_ids)),
                    ("insurance_claims", _query_for_ids(session, InsuranceClaim, InsuranceClaim.invoice_id, invoice_ids)),
                ]
                for entity, query in indirect_entities:
                    DataExportService._write_query(archive, entity, query, manifest_entities)

                manifest = {
                    "format": EXPORT_FORMAT,
                    "version": EXPORT_VERSION,
                    "classification": DataClassification.RESTRICTED,
                    "facility": {
                        "id": str(facility.id),
                        "slug": facility.slug,
                    },
                    "entities": manifest_entities,
                    "handling": {
                        "contains": "Restricted clinical and operational data",
                        "storage": "Generated on demand; no export artifact is retained by HIS.Pro",
                        "import": "Validate the manifest and reconcile counts before importing into another system",
                    },
                }
                archive.writestr(
                    "manifest.json",
                    json.dumps(_json_value(manifest), sort_keys=True, separators=(",", ":")).encode("utf-8"),
                )

            archive_file.seek(0)
            return DataExportArchive(
                file=archive_file,
                filename=f"hispro-{facility.slug}-export.zip",
                manifest=manifest,
            )
        except Exception:
            archive_file.close()
            raise

    @staticmethod
    def _write_query(
        archive: zipfile.ZipFile,
        entity: str,
        rows: Iterable[Any],
        manifest_entities: list[dict[str, Any]],
    ) -> None:
        digest = hashlib.sha256()
        count = 0
        path = f"entities/{entity}.json"

        def write(member, data: bytes) -> None:
            member.write(data)
            digest.update(data)

        with archive.open(path, "w") as member:
            write(member, b"[")
            iterator = rows.yield_per(QUERY_BATCH_SIZE) if hasattr(rows, "yield_per") else iter(rows)
            for record in iterator:
                if count:
                    write(member, b",")
                write(
                    member,
                    json.dumps(_record(record), sort_keys=True, separators=(",", ":")).encode("utf-8"),
                )
                count += 1
            write(member, b"]")

        manifest_entities.append(
            {
                "name": entity,
                "path": path,
                "records": count,
                "classification": classification_for_export_entity(entity),
                "sha256": digest.hexdigest(),
            }
        )

    @staticmethod
    def iter_archive(archive: DataExportArchive):
        try:
            while chunk := archive.file.read(CHUNK_SIZE):
                yield chunk
        finally:
            archive.file.close()
