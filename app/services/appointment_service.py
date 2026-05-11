from sqlalchemy import func
from app.models.appointment import Appointment
from app.extensions import db
from datetime import datetime

class AppointmentService:
    """Appointment service class"""
    
    @staticmethod
    def create_appointment(data):
        """Create a new appointment"""
        appointment = Appointment(
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            appointment_date=data['appointment_date'],
            reason=data.get('reason'),
            notes=data.get('notes')
        )
        appointment.save()
        return appointment
    
    @staticmethod
    def get_appointment_by_id(appointment_id):
        """Get appointment by ID"""
        return Appointment.query.get(appointment_id)
    
    @staticmethod
    def get_appointments_by_patient(patient_id, facility_slug=None):
        """Get all appointments for a patient, optionally filtered by facility"""
        query = Appointment.query.filter_by(patient_id=patient_id)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        return query.order_by(Appointment.appointment_date.desc()).all()

    @staticmethod
    def get_appointments_by_doctor(doctor_id, date=None, facility_slug=None):
        """Get appointments for a doctor, optionally filtered by date and facility"""
        query = Appointment.query.filter_by(doctor_id=doctor_id)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        if date:
            query = query.filter(func.date(Appointment.appointment_date) == date)
        return query.order_by(Appointment.appointment_date).all()
    
    @staticmethod
    def update_appointment_status(appointment, status):
        """Update appointment status"""
        appointment.status = status
        appointment.save()
        return appointment
    
    @staticmethod
    def update_appointment(appointment, data):
        """Update appointment fields"""
        for key, value in data.items():
            if hasattr(appointment, key) and value is not None:
                setattr(appointment, key, value)
        appointment.save()
        return appointment

    @staticmethod
    def cancel_appointment(appointment):
        """Cancel appointment"""
        appointment.status = 'CANCELLED'
        appointment.save()
        return appointment
