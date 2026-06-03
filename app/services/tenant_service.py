from __future__ import annotations

import logging
from typing import Iterable, Type

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.extensions import db_session
from app.models.alert import Alert
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.billing import Invoice
from app.models.facility import Facility
from app.models.inventory import Inventory
from app.models.lab import LabOrder
from app.models.medical_record import MedicalRecord
from app.models.order_workflow import OrderWorkflowEvent
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.models.patient_queue import PatientQueue
from app.models.pharmacy import Medication, Prescription
from app.models.radiology import Radiology
from app.models.supplier import Supplier
from app.models.user import User
from app.models.ward import WardAdmission, WardBed

logger = logging.getLogger(__name__)

TENANT_SCOPED_MODELS: tuple[Type, ...] = (
    User,
    Patient,
    Appointment,
    MedicalRecord,
    LabOrder,
    Medication,
    Prescription,
    Invoice,
    Radiology,
    Inventory,
    Supplier,
    PatientQueue,
    Alert,
    AuditLog,
    WardBed,
    WardAdmission,
    PatientNotification,
    OrderWorkflowEvent,
)


def resolve_facility_by_slug(facility_slug: str | None, session=None) -> Facility | None:
    if not facility_slug:
        return None
    session = session or db_session
    return session.query(Facility).filter_by(slug=facility_slug).first()


def resolve_facility_id(facility_slug: str | None, session=None) -> str | None:
    facility = resolve_facility_by_slug(facility_slug, session=session)
    return str(facility.id) if facility else None


def tenant_filter_kwargs(facility: Facility) -> dict[str, str]:
    return {"facility_id": str(facility.id), "facility_slug": facility.slug}


def populate_tenant_id(obj, session: Session) -> None:
    if not hasattr(obj, "facility_id") or getattr(obj, "facility_id", None):
        return

    facility_slug = getattr(obj, "facility_slug", None)
    if not facility_slug:
        return

    cache = getattr(session, "_hispro_tenant_slug_cache", None)
    if cache is None:
        cache = {}
        setattr(session, "_hispro_tenant_slug_cache", cache)

    if facility_slug not in cache:
        cache[facility_slug] = resolve_facility_id(facility_slug, session=session)

    if cache[facility_slug]:
        setattr(obj, "facility_id", cache[facility_slug])


def register_tenant_hooks() -> None:
    if getattr(register_tenant_hooks, "_registered", False):
        return

    @event.listens_for(Session, "before_flush")
    def _populate_tenant_ids(session, flush_context, instances):
        for obj in list(session.new) + list(session.dirty):
            populate_tenant_id(obj, session)

    register_tenant_hooks._registered = True


def backfill_facility_ids(models: Iterable[Type] = TENANT_SCOPED_MODELS) -> int:
    facilities = {
        facility.slug: str(facility.id)
        for facility in db_session.query(Facility).all()
    }
    if not facilities:
        return 0

    updated = 0
    for model in models:
        if not hasattr(model, "facility_id") or not hasattr(model, "facility_slug"):
            continue
        rows = (
            db_session.query(model)
            .filter(model.facility_id == None, model.facility_slug.in_(facilities.keys()))
            .all()
        )
        for row in rows:
            row.facility_id = facilities.get(row.facility_slug)
            if row.facility_id:
                db_session.add(row)
                updated += 1

    if updated:
        db_session.commit()
        logger.info("Backfilled facility_id on %s tenant-scoped row(s)", updated)
    return updated

