from sqlalchemy import or_

from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.extensions import db
from datetime import date

class PatientService:
    """Patient service class with business logic"""
    
    @staticmethod
    def create_patient(data, user_id, facility_slug=None):
        """Create a new patient"""
        date_of_birth = data['date_of_birth']
        if isinstance(date_of_birth, str):
            date_of_birth = date.fromisoformat(date_of_birth)

        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=date_of_birth,
            gender=data.get('gender'),
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            blood_type=data.get('blood_type'),
            medical_history=data.get('medical_history', {}),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            created_by=user_id,
            facility_slug=facility_slug
        )
        patient.save()
        return patient
    
    @staticmethod
    def get_patient_by_id(patient_id, facility_slug=None):
        """Get patient by ID"""
        query = Patient.query
        if facility_slug:
            query = query.filter_by(id=patient_id, facility_slug=facility_slug)
            return query.first()
        return Patient.query.get(patient_id)
    
    @staticmethod
    def get_all_patients(facility_slug=None, page=1, per_page=20, search=None, current_user=None):
        """Get paginated list of patients with optional facility filtering"""
        query = Patient.query

        # Filter by facility_slug for multi-tenant isolation
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug, is_active=True)
        else:
            query = query.filter_by(is_active=True)

        if search:
            query = query.filter(
                Patient.first_name.ilike(f'%{search}%') |
                Patient.last_name.ilike(f'%{search}%')
            )

        query = PatientService.apply_patient_access_filter(query, facility_slug, current_user)

        query = query.order_by(Patient.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }
    
    @staticmethod
    def update_patient(patient, data):
        """Update patient information"""
        for key, value in data.items():
            if key == 'date_of_birth' and isinstance(value, str):
                value = date.fromisoformat(value)
            if hasattr(patient, key) and value is not None:
                setattr(patient, key, value)
        patient.save()
        return patient
    
    @staticmethod
    def delete_patient(patient):
        """Soft delete patient"""
        patient.is_active = False
        patient.save()
        return True

    @staticmethod
    def apply_patient_access_filter(query, facility_slug, current_user):
        """Limit patient list results by clinical assignment for patient privacy."""
        if not current_user:
            return query.filter(False)

        role = (current_user.role or "").upper()
        if role in {"ADMIN", "RECEPTIONIST", "NURSE"}:
            return query

        if role != "DOCTOR":
            return query.filter(False)

        assigned_appointments = db.session.query(Appointment.patient_id).filter(
            Appointment.facility_slug == facility_slug,
            Appointment.doctor_id == current_user.id,
        )
        authored_records = db.session.query(MedicalRecord.patient_id).filter(
            MedicalRecord.facility_slug == facility_slug,
            MedicalRecord.created_by == current_user.id,
        )

        return query.filter(
            or_(
                Patient.created_by == current_user.id,
                Patient.id.in_(assigned_appointments),
                Patient.id.in_(authored_records),
            )
        )

    @staticmethod
    def user_can_access_patient(patient_id, facility_slug, current_user):
        """Return True when a user can view a specific patient in their facility."""
        if not current_user or current_user.facility_slug != facility_slug:
            return False

        role = (current_user.role or "").upper()
        if role in {"ADMIN", "RECEPTIONIST", "NURSE"}:
            return True

        if role != "DOCTOR":
            return False

        if Patient.query.filter_by(
            id=patient_id,
            facility_slug=facility_slug,
            created_by=current_user.id,
            is_active=True,
        ).first():
            return True

        has_appointment = Appointment.query.filter_by(
            patient_id=patient_id,
            doctor_id=current_user.id,
            facility_slug=facility_slug,
        ).first()
        if has_appointment:
            return True

        return bool(
            MedicalRecord.query.filter_by(
                patient_id=patient_id,
                created_by=current_user.id,
                facility_slug=facility_slug,
            ).first()
        )
