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
    def get_appointments_by_patient(patient_id):
        """Get all appointments for a patient"""
        return Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).all()
    
    @staticmethod
    def get_appointments_by_doctor(doctor_id, date=None):
        """Get appointments for a doctor, optionally filtered by date"""
        query = Appointment.query.filter_by(doctor_id=doctor_id)
        
        if date:
            query = query.filter(db.func.date(Appointment.appointment_date) == date)
        
        return query.order_by(Appointment.appointment_date).all()
    
    @staticmethod
    def update_appointment_status(appointment, status):
        """Update appointment status"""
        appointment.status = status
        appointment.save()
        return appointment
    
    @staticmethod
    def cancel_appointment(appointment):
        """Cancel appointment"""
        appointment.status = 'CANCELLED'
        appointment.save()
        return appointment
