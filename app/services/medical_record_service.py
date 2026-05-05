from app.models.medical_record import MedicalRecord, ClinicalNote
from app.extensions import db

class MedicalRecordService:
    """Medical Records service class"""
    
    # ==================== Medical Records ====================
    
    @staticmethod
    def create_medical_record(data, created_by_id):
        """Create a new medical record"""
        record = MedicalRecord(
            patient_id=data['patient_id'],
            appointment_id=data.get('appointment_id'),
            created_by=created_by_id,
            chief_complaint=data.get('chief_complaint'),
            vital_signs=data.get('vital_signs', {}),
            symptoms=data.get('symptoms', []),
            diagnosis=data.get('diagnosis', []),
            treatment_plan=data.get('treatment_plan'),
            prescriptions=data.get('prescriptions', []),
            lab_orders=data.get('lab_orders', []),
            follow_up_date=data.get('follow_up_date'),
            notes=data.get('notes')
        )
        record.save()
        return record
    
    @staticmethod
    def get_medical_record_by_id(record_id):
        """Get medical record by ID"""
        return MedicalRecord.query.get(record_id)
    
    @staticmethod
    def get_medical_records_by_patient(patient_id):
        """Get all medical records for a patient"""
        return MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.created_at.desc()).all()
    
    @staticmethod
    def update_medical_record(record, data):
        """Update medical record"""
        for key, value in data.items():
            if hasattr(record, key) and value is not None:
                setattr(record, key, value)
        record.save()
        return record
    
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
