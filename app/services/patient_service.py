from app.models.patient import Patient
from app.extensions import db

class PatientService:
    """Patient service class with business logic"""
    
    @staticmethod
    def create_patient(data, user_id, facility_slug=None):
        """Create a new patient"""
        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            date_of_birth=data['date_of_birth'],
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
    def get_all_patients(facility_slug=None, page=1, per_page=20, search=None):
        """Get paginated list of patients with optional facility filtering"""
        query = Patient.query

        # Filter by facility_slug for multi-tenant isolation
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)

        if search:
            query = query.filter(
                Patient.first_name.ilike(f'%{search}%') |
                Patient.last_name.ilike(f'%{search}%')
            )

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
            if hasattr(patient, key) and value is not None:
                setattr(patient, key, value)
        patient.save()
        return patient
    
    @staticmethod
    def delete_patient(patient):
        """Soft delete patient"""
        patient.delete()
        return True
