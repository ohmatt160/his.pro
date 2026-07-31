from datetime import date, datetime
from sqlalchemy.exc import IntegrityError

from app.models.base_model import utc_now
from app.models.medical_record import MedicalRecord, ClinicalNote
from app.extensions import db
from app.utils.idempotency import verify_idempotent_replay

class MedicalRecordService:
    """Medical Records service class"""

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.fromisoformat(str(value)).date()
    
    # ==================== Medical Records ====================
    
    @staticmethod
    def create_medical_record(
        data,
        created_by_id,
        facility_slug,
        facility_id=None,
        idempotency_key=None,
        payload_hash=None,
    ):
        """Create a new medical record"""
        existing = MedicalRecord.query.filter_by(
            facility_slug=facility_slug,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return verify_idempotent_replay(existing, payload_hash), False

        record = MedicalRecord(
            patient_id=data['patient_id'],
            appointment_id=data.get('appointment_id'),
            facility_id=facility_id,
            facility_slug=facility_slug,
            created_by=created_by_id,
            chief_complaint=data.get('chief_complaint'),
            vital_signs=data.get('vital_signs', {}),
            symptoms=data.get('symptoms', []),
            diagnosis=data.get('diagnosis', []),
            treatment_plan=data.get('treatment_plan'),
            prescriptions=data.get('prescriptions', []),
            lab_orders=data.get('lab_orders', []),
            follow_up_date=MedicalRecordService._parse_date(data.get('follow_up_date')),
            notes=data.get('notes'),
            idempotency_key=idempotency_key,
            idempotency_payload_hash=payload_hash,
        )
        try:
            record.save()
            return record, True
        except IntegrityError:
            db.session.rollback()
            existing = MedicalRecord.query.filter_by(
                facility_slug=facility_slug,
                idempotency_key=idempotency_key,
            ).first()
            if not existing:
                raise
            return verify_idempotent_replay(existing, payload_hash), False
    
    @staticmethod
    def get_medical_record_by_id(record_id):
        """Get medical record by ID"""
        return MedicalRecord.query.get(record_id)
    
    @staticmethod
    def get_medical_records_by_patient(patient_id, facility_slug):
        """Get all medical records for a patient"""
        return MedicalRecord.query.filter_by(
            patient_id=patient_id,
            facility_slug=facility_slug,
        ).order_by(MedicalRecord.created_at.desc()).all()

    @staticmethod
    def get_medical_records_by_facility(facility_slug):
        """Get all medical records for a facility"""
        return MedicalRecord.query.filter_by(
            facility_slug=facility_slug,
        ).order_by(MedicalRecord.created_at.desc()).all()
    
    @staticmethod
    def update_medical_record(record, data):
        """Update medical record"""
        if record.status == "VOIDED":
            raise ValueError("Voided medical records cannot be edited")
        if 'follow_up_date' in data:
            data['follow_up_date'] = MedicalRecordService._parse_date(data['follow_up_date'])

        for key, value in data.items():
            if hasattr(record, key) and value is not None:
                setattr(record, key, value)
        record.save()
        return record

    @staticmethod
    def void_medical_record(record, *, reason, voided_by):
        """Void a medical record while preserving its clinical and audit history."""
        if record.status == "VOIDED":
            return record, False
        record.status = "VOIDED"
        record.void_reason = reason
        record.voided_by = voided_by
        record.voided_at = utc_now()
        record.save()
        return record, True
    
    # ==================== Clinical Notes ====================
    
    @staticmethod
    def create_clinical_note(data, created_by_id):
        """Create a new clinical note"""
        note = ClinicalNote(
            patient_id=data['patient_id'],
            record_id=data.get('record_id'),
            created_by=created_by_id,
            note_type=data.get('note_type', 'PROGRESS'),
            title=data.get('title'),
            content=data['content'],
            is_confidential=data.get('is_confidential', False)
        )
        note.save()
        return note
    
    @staticmethod
    def get_clinical_notes_by_patient(patient_id):
        """Get all clinical notes for a patient"""
        return ClinicalNote.query.filter_by(patient_id=patient_id).order_by(ClinicalNote.created_at.desc()).all()
    
    @staticmethod
    def get_clinical_note_by_id(note_id):
        """Get clinical note by ID"""
        return ClinicalNote.query.get(note_id)
    
    @staticmethod
    def update_clinical_note(note, data):
        """Update clinical note"""
        for key, value in data.items():
            if hasattr(note, key) and value is not None:
                setattr(note, key, value)
        note.save()
        return note
