"""Tenant account deletion, recovery, and final-purge lifecycle controls."""

from __future__ import annotations

import hashlib
import hmac
import html
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.background_job import BackgroundJob
from app.models.billing import InsuranceClaim, Invoice, InvoiceItem, Payment
from app.models.branch import Branch
from app.models.facility import Facility
from app.models.hospital_listing import HospitalListing
from app.models.integration_outbox import IntegrationOutbox
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
from app.models.user_session import UserSession
from app.models.ward import WardAdmission, WardBed
from app.models.write_idempotency import WriteIdempotencyRecord
from app.services.email_service import EmailService


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _retention_days() -> int:
    raw_days = os.getenv("ACCOUNT_DELETION_RETENTION_DAYS", "30")
    try:
        days = int(raw_days)
    except ValueError as exc:
        raise RuntimeError("ACCOUNT_DELETION_RETENTION_DAYS must be an integer") from exc
    if not 1 <= days <= 90:
        raise RuntimeError("ACCOUNT_DELETION_RETENTION_DAYS must be between 1 and 90")
    return days


def _is_production_like() -> bool:
    return (os.getenv("APP_ENV") or os.getenv("FLASK_ENV", "development")).lower() in {
        "production",
        "staging",
    }


def _recovery_origin() -> str:
    origin = (os.getenv("PUBLIC_APP_ORIGIN") or os.getenv("FRONTEND_URL") or "").strip().rstrip("/")
    if origin.startswith("https://") or (not _is_production_like() and origin.startswith("http://")):
        return origin
    if not _is_production_like():
        return "http://localhost:5173"
    raise RuntimeError("PUBLIC_APP_ORIGIN or FRONTEND_URL must be an HTTPS origin")


def _can_expose_recovery_token() -> bool:
    return not _is_production_like() and (
        os.getenv("TESTING", "").lower() == "true"
        or os.getenv("ACCOUNT_DELETION_EXPOSE_RECOVERY_TOKEN", "").lower() == "true"
    )


def _tenant_filter(model, facility: Facility):
    columns = model.__table__.columns
    clauses = []
    if "facility_id" in columns:
        clauses.append(model.facility_id == facility.id)
    if "facility_slug" in columns:
        clauses.append(model.facility_slug == facility.slug)
    if not clauses:
        raise ValueError(f"{model.__tablename__} is not tenant-scoped")
    return or_(*clauses)


def _delete_tenant_rows(session: Session, model, facility: Facility) -> int:
    return session.query(model).filter(_tenant_filter(model, facility)).delete(
        synchronize_session=False,
    )


class FacilityLifecycleService:
    """Enforce a reversible retention window before an account is purged."""

    @staticmethod
    def request_deletion(
        session: Session,
        *,
        facility: Facility,
        actor: User,
        password: str,
        confirmation_name: str,
    ) -> dict:
        if facility.deletion_status == "PURGED":
            raise HTTPException(status_code=410, detail="Facility account is no longer available")
        if facility.deletion_status == "PENDING_DELETION":
            return {
                "status": "pending_deletion",
                "scheduled_for": facility.deletion_scheduled_for.isoformat()
                if facility.deletion_scheduled_for
                else None,
                "retention_days": _retention_days(),
                "already_requested": True,
            }
        if not facility.is_active:
            raise HTTPException(status_code=409, detail="Facility account is unavailable")
        if not actor.check_password(password):
            raise HTTPException(status_code=403, detail="Password confirmation failed")
        if not hmac.compare_digest((confirmation_name or "").strip(), (facility.name or "").strip()):
            raise HTTPException(status_code=400, detail="Facility name confirmation does not match")

        now = utc_now()
        retention_days = _retention_days()
        scheduled_for = now + timedelta(days=retention_days)
        recovery_token = secrets.token_urlsafe(48)
        facility.deletion_status = "PENDING_DELETION"
        facility.deletion_requested_at = now
        facility.deletion_scheduled_for = scheduled_for
        facility.deletion_cancelled_at = None
        facility.deletion_requested_by_id = actor.id
        facility.deletion_recovery_token_hash = hashlib.sha256(
            recovery_token.encode("utf-8")
        ).hexdigest()
        facility.is_active = False

        users = session.query(User).filter(_tenant_filter(User, facility)).all()
        user_ids = [user.id for user in users]
        if user_ids:
            session.query(UserSession).filter(
                UserSession.user_id.in_(user_ids),
                UserSession.is_active == True,
            ).update(
                {"is_active": False, "revoked_at": now},
                synchronize_session=False,
            )

        job = BackgroundJob(
            name="facility_deletion_purge",
            facility_id=facility.id,
            requested_by_user_id=actor.id,
            idempotency_key=f"facility-purge:{facility.id}:{uuid.uuid4()}",
            payload_json={"deletion_requested_at": now.isoformat()},
            status="QUEUED",
            attempts=0,
            max_attempts=10,
            available_at=scheduled_for,
        )
        session.add(facility)
        session.add(job)
        session.flush()

        origin = _recovery_origin()
        recovery_url = (
            f"{origin}/recover-account?facility={quote(facility.slug)}"
            f"#token={quote(recovery_token)}"
        )
        sent, message = EmailService.send_email(
            actor.email,
            "HIS.Pro account deletion scheduled",
            (
                f"The deletion of {facility.name} has been scheduled for {scheduled_for.isoformat()} UTC.\n\n"
                "All sessions have been revoked. To cancel the deletion during the retention window, open:\n"
                f"{recovery_url}\n\n"
                "Keep this link private. If you did not request this, contact HIS.Pro support immediately."
            ),
            (
                "<p>Your HIS.Pro facility account has been scheduled for deletion.</p>"
                f"<p><strong>Scheduled purge:</strong> {html.escape(scheduled_for.isoformat())} UTC</p>"
                f'<p><a href="{html.escape(recovery_url, quote=True)}">Cancel account deletion</a></p>'
                "<p>Keep this recovery link private. If this was not you, contact HIS.Pro support immediately.</p>"
            ),
        )
        if not sent and _is_production_like():
            raise HTTPException(
                status_code=503,
                detail="Account deletion could not be scheduled because recovery email delivery is unavailable",
            )

        result = {
            "status": "pending_deletion",
            "scheduled_for": scheduled_for.isoformat(),
            "retention_days": retention_days,
            "recovery_delivery": "sent" if sent else "not_configured",
            "job_id": str(job.id),
        }
        if _can_expose_recovery_token():
            result["recovery_token"] = recovery_token
            result["recovery_url"] = recovery_url
        return result

    @staticmethod
    def recover_deletion(
        session: Session,
        *,
        facility: Facility,
        recovery_token: str,
    ) -> dict:
        expected_hash = facility.deletion_recovery_token_hash or ""
        supplied_hash = hashlib.sha256(recovery_token.encode("utf-8")).hexdigest()
        if (
            facility.deletion_status != "PENDING_DELETION"
            or not expected_hash
            or not hmac.compare_digest(expected_hash, supplied_hash)
            or not facility.deletion_scheduled_for
            or facility.deletion_scheduled_for <= utc_now()
        ):
            raise HTTPException(status_code=400, detail="Recovery link is invalid or has expired")

        facility.deletion_status = "ACTIVE"
        facility.deletion_cancelled_at = utc_now()
        facility.deletion_requested_at = None
        facility.deletion_scheduled_for = None
        facility.deletion_requested_by_id = None
        facility.deletion_recovery_token_hash = None
        facility.is_active = True
        session.query(BackgroundJob).filter(
            BackgroundJob.facility_id == facility.id,
            BackgroundJob.name == "facility_deletion_purge",
            BackgroundJob.status.in_(("QUEUED", "RETRY")),
        ).update({"status": "CANCELLED"}, synchronize_session=False)
        session.add(facility)
        session.flush()
        return {
            "status": "active",
            "message": "Account deletion was cancelled. Sign in again to start a new session.",
        }

    @staticmethod
    def purge_scheduled_facility(
        session: Session,
        *,
        facility_id: str,
        background_job: BackgroundJob,
    ) -> dict:
        facility = session.query(Facility).filter(Facility.id == facility_id).first()
        if not facility:
            return {"status": "already_removed"}
        if facility.deletion_status == "PURGED":
            return {"status": "already_purged"}
        if facility.deletion_status != "PENDING_DELETION" or not facility.deletion_scheduled_for:
            return {"status": "cancelled"}
        if facility.deletion_scheduled_for > utc_now():
            raise RuntimeError("Facility deletion retention window has not elapsed")

        original_slug = facility.slug
        counts = FacilityLifecycleService._purge_tenant_rows(
            session,
            facility,
            background_job=background_job,
        )

        tombstone_slug = f"deleted-{str(facility.id).replace('-', '')[:20]}"
        facility.name = "Deleted facility"
        facility.slug = tombstone_slug
        facility.canonical_subdomain = tombstone_slug
        facility.country = ""
        facility.address = ""
        facility.phone = ""
        facility.email = ""
        facility.departments = []
        facility.modules = []
        facility.settings = {}
        facility.is_active = False
        facility.deletion_status = "PURGED"
        facility.deletion_recovery_token_hash = None
        facility.deletion_scheduled_for = None
        facility.deletion_requested_at = None
        facility.deletion_cancelled_at = utc_now()
        session.add(facility)
        session.add(
            BackgroundJob(
                name="facility_storage_purge",
                facility_id=facility.id,
                requested_by_user_id=background_job.requested_by_user_id,
                idempotency_key=f"facility-storage-purge:{facility.id}",
                payload_json={"facility_slug": original_slug},
                status="QUEUED",
                attempts=0,
                max_attempts=10,
                available_at=utc_now(),
            )
        )
        session.flush()
        return {
            "status": "purged",
            "purged_at": utc_now().isoformat(),
            "records_removed": counts,
        }

    @staticmethod
    def _purge_tenant_rows(
        session: Session,
        facility: Facility,
        *,
        background_job: BackgroundJob,
    ) -> dict[str, int]:
        """Delete data leaf-first, preserving only anonymized identity tombstones."""
        counts: dict[str, int] = {}
        patient_ids = session.query(Patient.id).filter(_tenant_filter(Patient, facility)).subquery()
        record_ids = session.query(MedicalRecord.id).filter(_tenant_filter(MedicalRecord, facility)).subquery()
        lab_order_ids = session.query(LabOrder.id).filter(_tenant_filter(LabOrder, facility)).subquery()
        medication_ids = session.query(Medication.id).filter(_tenant_filter(Medication, facility)).subquery()
        prescription_ids = session.query(Prescription.id).filter(_tenant_filter(Prescription, facility)).subquery()
        invoice_ids = session.query(Invoice.id).filter(_tenant_filter(Invoice, facility)).subquery()
        conversation_ids = session.query(ChatConversation.id).filter(_tenant_filter(ChatConversation, facility)).subquery()
        user_ids = session.query(User.id).filter(_tenant_filter(User, facility)).subquery()

        counts["clinical_notes"] = session.query(ClinicalNote).filter(
            or_(ClinicalNote.patient_id.in_(patient_ids), ClinicalNote.record_id.in_(record_ids))
        ).delete(synchronize_session=False)
        counts["lab_results"] = session.query(LabResult).filter(
            LabResult.order_id.in_(lab_order_ids)
        ).delete(synchronize_session=False)
        counts["pharmacy_inventory"] = session.query(PharmacyInventory).filter(
            PharmacyInventory.medication_id.in_(medication_ids)
        ).delete(synchronize_session=False)
        counts["prescription_items"] = session.query(PrescriptionItem).filter(
            PrescriptionItem.prescription_id.in_(prescription_ids)
        ).delete(synchronize_session=False)
        counts["invoice_items"] = session.query(InvoiceItem).filter(
            InvoiceItem.invoice_id.in_(invoice_ids)
        ).delete(synchronize_session=False)
        counts["payments"] = session.query(Payment).filter(
            Payment.invoice_id.in_(invoice_ids)
        ).delete(synchronize_session=False)
        counts["insurance_claims"] = session.query(InsuranceClaim).filter(
            InsuranceClaim.invoice_id.in_(invoice_ids)
        ).delete(synchronize_session=False)
        counts["chat_messages"] = session.query(ChatMessage).filter(
            or_(ChatMessage.conversation_id.in_(conversation_ids), _tenant_filter(ChatMessage, facility))
        ).delete(synchronize_session=False)
        counts["user_sessions"] = session.query(UserSession).filter(
            UserSession.user_id.in_(user_ids)
        ).delete(synchronize_session=False)

        for label, model in (
            ("alerts", Alert),
            ("audit_logs", AuditLog),
            ("patient_notifications", PatientNotification),
            ("order_workflow_events", OrderWorkflowEvent),
            ("referrals", Referral),
            ("patient_queues", PatientQueue),
            ("ward_admissions", WardAdmission),
            ("integration_outbox", IntegrationOutbox),
            ("write_idempotency", WriteIdempotencyRecord),
        ):
            counts[label] = _delete_tenant_rows(session, model, facility)

        counts["background_jobs"] = session.query(BackgroundJob).filter(
            BackgroundJob.facility_id == facility.id,
            BackgroundJob.id != background_job.id,
        ).delete(synchronize_session=False)

        for label, model in (
            ("chat_conversations", ChatConversation),
            ("medical_records", MedicalRecord),
            ("lab_orders", LabOrder),
            ("lab_tests", LabTest),
            ("prescriptions", Prescription),
            ("medications", Medication),
            ("invoices", Invoice),
            ("appointments", Appointment),
            ("radiology_orders", Radiology),
            ("ward_beds", WardBed),
            ("inventory", Inventory),
            ("suppliers", Supplier),
            ("hospital_listings", HospitalListing),
            ("patients", Patient),
        ):
            counts[label] = _delete_tenant_rows(session, model, facility)

        # Users are retained only as non-login, non-identifying tombstones to
        # satisfy existing foreign keys on the deletion record and current job.
        users = session.query(User).filter(_tenant_filter(User, facility)).all()
        for user in users:
            suffix = str(user.id).replace("-", "")[:20]
            user.username = f"deleted-{suffix}"
            user.email = f"deleted-{suffix}@invalid.hispro.local"
            user.password_hash = secrets.token_urlsafe(64)
            user.is_active = False
            user.first_name = None
            user.last_name = None
            user.phone = None
            user.department = None
            user.department_id = None
            user.departments = []
            user.branch_id = None
            user.branch_ids = []
            user.facility_slug = None
            session.add(user)
        counts["users_anonymized"] = len(users)

        counts["branches"] = _delete_tenant_rows(session, Branch, facility)
        return counts
