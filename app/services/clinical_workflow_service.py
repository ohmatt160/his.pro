import re
from datetime import datetime

from app.extensions import db_session
from app.models.alert import Alert
from app.models.lab import LabOrder, LabTest
from app.models.patient import Patient
from app.models.pharmacy import Medication, Prescription, PrescriptionItem
from app.models.radiology import Radiology
from app.models.user import User
from app.services.order_workflow_service import OrderWorkflowService
from app.utils.validators import Validators


class ClinicalWorkflowService:
    """Create downstream clinical work from consultation orders."""

    @staticmethod
    def sync_consultation_orders(record, current_user):
        created = {
            "lab_orders": [],
            "radiology_orders": [],
            "prescriptions": [],
        }
        created["lab_orders"] = ClinicalWorkflowService._sync_lab_orders(record, current_user)
        created["radiology_orders"] = ClinicalWorkflowService._sync_radiology_orders(record, current_user)
        created["prescriptions"] = ClinicalWorkflowService._sync_prescriptions(record, current_user)
        return created

    @staticmethod
    def notify_roles(facility_slug: str, roles: list[str], alert_type: str, title: str, message: str):
        users = (
            db_session.query(User)
            .filter(User.facility_slug == facility_slug, User.is_active == True, User.role.in_(roles))
            .all()
        )
        created = []
        for user in users:
            alert = Alert(
                facility_slug=facility_slug,
                alert_type=alert_type,
                title=Validators.sanitize_string(title),
                message=Validators.sanitize_string(message),
                recipient_id=user.id,
            )
            db_session.add(alert)
            created.append(alert)
        db_session.flush()
        return created

    @staticmethod
    def notify_user(user_id: str | None, facility_slug: str, alert_type: str, title: str, message: str):
        if not user_id:
            return None
        alert = Alert(
            facility_slug=facility_slug,
            alert_type=alert_type,
            title=Validators.sanitize_string(title),
            message=Validators.sanitize_string(message),
            recipient_id=user_id,
        )
        db_session.add(alert)
        db_session.flush()
        return alert

    @staticmethod
    def _sync_lab_orders(record, current_user):
        created = []
        patient_name = ClinicalWorkflowService._patient_name(record.patient)
        for order in ClinicalWorkflowService._plain_orders(record.lab_orders, excluded_type="radiology"):
            test_name = ClinicalWorkflowService._order_name(order, "test")
            if not test_name:
                continue
            marker = ClinicalWorkflowService._marker("consultation", record.id, "lab", test_name)
            if ClinicalWorkflowService._existing_lab_order(record, marker):
                continue

            test = ClinicalWorkflowService._ensure_lab_test(
                test_name,
                record.facility_slug,
                record.facility_id,
            )
            lab_order = LabOrder(
                patient_id=record.patient_id,
                test_id=test.id,
                facility_slug=record.facility_slug,
                ordered_by=current_user.id,
                priority=ClinicalWorkflowService._lab_priority(order),
                notes=f"{marker}\n{Validators.sanitize_string(str(order.get('notes') or 'Consultation order'))}",
                order_date=datetime.utcnow(),
            )
            db_session.add(lab_order)
            db_session.flush()
            OrderWorkflowService.record(
                facility_slug=record.facility_slug,
                patient_id=record.patient_id,
                order_type="lab",
                order_id=lab_order.id,
                event_type="consultation_order_created",
                status="PENDING",
                title="Consultation lab order created",
                message=f"{test_name} ordered from consultation.",
                actor_id=current_user.id,
                target_role="LAB_TECH",
                metadata={"consultation_id": record.id, "test_name": test_name},
            )
            created.append(lab_order)

        if created:
            ClinicalWorkflowService.notify_roles(
                record.facility_slug,
                ["LAB_TECH", "ADMIN"],
                "info",
                "New lab order",
                f"{len(created)} lab order(s) for {patient_name}",
            )
        return created

    @staticmethod
    def _sync_radiology_orders(record, current_user):
        created = []
        patient_name = ClinicalWorkflowService._patient_name(record.patient)
        for order in ClinicalWorkflowService._radiology_orders(record.lab_orders):
            study = ClinicalWorkflowService._order_name(order, "study")
            if not study:
                continue
            modality, body_part = ClinicalWorkflowService._parse_study(study)
            marker = ClinicalWorkflowService._marker("consultation", record.id, "radiology", study)
            if ClinicalWorkflowService._existing_radiology_order(record, marker):
                continue

            radiology = Radiology(
                patient_id=record.patient_id,
                facility_slug=record.facility_slug,
                modality=modality,
                body_part=body_part,
                clinical_notes=f"{marker}\n{Validators.sanitize_string(str(order.get('notes') or 'Consultation imaging order'))}",
                requested_by=current_user.id,
                status="pending",
            )
            db_session.add(radiology)
            db_session.flush()
            OrderWorkflowService.record(
                facility_slug=record.facility_slug,
                patient_id=record.patient_id,
                order_type="radiology",
                order_id=radiology.id,
                event_type="consultation_order_created",
                status="pending",
                title="Consultation radiology order created",
                message=f"{modality} {body_part} ordered from consultation.",
                actor_id=current_user.id,
                target_role="RADIOLOGIST",
                metadata={"consultation_id": record.id, "study": study},
            )
            created.append(radiology)

        if created:
            ClinicalWorkflowService.notify_roles(
                record.facility_slug,
                ["RADIOLOGIST", "ADMIN"],
                "info",
                "New radiology order",
                f"{len(created)} imaging order(s) for {patient_name}",
            )
        return created

    @staticmethod
    def _sync_prescriptions(record, current_user):
        items = []
        markers = []
        for order in record.prescriptions or []:
            medication_name = ClinicalWorkflowService._order_name(order, "medication")
            if not medication_name:
                continue
            marker = ClinicalWorkflowService._marker("consultation", record.id, "prescription", medication_name)
            if ClinicalWorkflowService._existing_prescription_item(record, marker):
                continue
            medication = ClinicalWorkflowService._ensure_medication(medication_name, record.facility_slug)
            items.append(
                PrescriptionItem(
                    medication_id=medication.id,
                    quantity=max(int(order.get("quantity") or 1), 1),
                    dosage=Validators.sanitize_string(str(order.get("dosage") or "")) or None,
                    instructions=Validators.sanitize_string(str(order.get("instructions") or "")) or None,
                )
            )
            markers.append(marker)

        if not items:
            return []

        prescription = Prescription(
            patient_id=record.patient_id,
            prescribed_by=current_user.id,
            facility_slug=record.facility_slug,
            notes="\n".join(markers),
            prescription_date=datetime.utcnow(),
        )
        db_session.add(prescription)
        db_session.flush()
        for item in items:
            item.prescription_id = prescription.id
            db_session.add(item)
        OrderWorkflowService.record(
            facility_slug=record.facility_slug,
            patient_id=record.patient_id,
            order_type="prescription",
            order_id=prescription.id,
            event_type="consultation_order_created",
            status="PENDING",
            title="Consultation prescription created",
            message="Prescription created from consultation medication orders.",
            actor_id=current_user.id,
            target_role="PHARMACIST",
            metadata={"consultation_id": record.id, "items": len(items)},
        )

        ClinicalWorkflowService.notify_roles(
            record.facility_slug,
            ["PHARMACIST", "ADMIN"],
            "info",
            "New prescription",
            f"Prescription ready for {ClinicalWorkflowService._patient_name(record.patient)}",
        )
        return [prescription]

    @staticmethod
    def _ensure_lab_test(name: str, facility_slug: str, facility_id: str | None = None) -> LabTest:
        code = ClinicalWorkflowService._code("LAB", f"{facility_slug}-{name}")
        test = db_session.query(LabTest).filter_by(
            code=code,
            facility_slug=facility_slug,
        ).first()
        if test:
            return test
        test = LabTest(
            name=name,
            code=code,
            category="Consultation",
            is_active=True,
            facility_id=facility_id,
            facility_slug=facility_slug,
        )
        db_session.add(test)
        db_session.flush()
        return test

    @staticmethod
    def _ensure_medication(name: str, facility_slug: str) -> Medication:
        code = ClinicalWorkflowService._code("MED", f"{facility_slug}-{name}")
        medication = db_session.query(Medication).filter_by(code=code, facility_slug=facility_slug).first()
        if medication:
            return medication
        medication = Medication(
            name=name,
            code=code,
            category="Consultation",
            unit="item",
            facility_slug=facility_slug,
            is_active=True,
        )
        db_session.add(medication)
        db_session.flush()
        return medication

    @staticmethod
    def _plain_orders(orders, excluded_type=None):
        return [
            order
            for order in (orders or [])
            if isinstance(order, dict) and (not excluded_type or order.get("type") != excluded_type)
        ]

    @staticmethod
    def _radiology_orders(orders):
        return [
            order
            for order in (orders or [])
            if isinstance(order, dict) and order.get("type") == "radiology"
        ]

    @staticmethod
    def _order_name(order, preferred_key: str) -> str:
        value = order.get(preferred_key) or order.get("name") or order.get("label")
        return Validators.sanitize_string(str(value or "")).strip()

    @staticmethod
    def _lab_priority(order) -> str:
        value = str(order.get("priority") or "ROUTINE").upper()
        return value if value in {"ROUTINE", "URGENT", "STAT"} else "ROUTINE"

    @staticmethod
    def _parse_study(study: str) -> tuple[str, str]:
        for modality in Radiology.MODALITIES:
            if study.lower().startswith(modality.lower()):
                body_part = study[len(modality):].strip(" -:") or "Unspecified"
                return modality, body_part
        return "X-ray", study

    @staticmethod
    def _marker(source: str, source_id: str, order_type: str, name: str) -> str:
        return f"[source={source}:{source_id};type={order_type};name={name.lower()}]"

    @staticmethod
    def _existing_lab_order(record, marker: str):
        return db_session.query(LabOrder).filter(
            LabOrder.facility_slug == record.facility_slug,
            LabOrder.patient_id == record.patient_id,
            LabOrder.notes.contains(marker),
        ).first()

    @staticmethod
    def _existing_radiology_order(record, marker: str):
        return db_session.query(Radiology).filter(
            Radiology.facility_slug == record.facility_slug,
            Radiology.patient_id == record.patient_id,
            Radiology.clinical_notes.contains(marker),
        ).first()

    @staticmethod
    def _existing_prescription_item(record, marker: str):
        return db_session.query(Prescription).filter(
            Prescription.facility_slug == record.facility_slug,
            Prescription.patient_id == record.patient_id,
            Prescription.notes.contains(marker),
        ).first()

    @staticmethod
    def _code(prefix: str, value: str) -> str:
        slug = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
        return f"{prefix}-{slug[:44]}"

    @staticmethod
    def _patient_name(patient: Patient | None) -> str:
        return patient.full_name if patient else "patient"
