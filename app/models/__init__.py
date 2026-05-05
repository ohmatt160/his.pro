# Import all models for easy access
from app.models.base_model import BaseModel
from app.models.user import User
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.billing import Invoice, InvoiceItem, Payment, InsuranceProvider, InsuranceClaim
from app.models.lab import LabTest, LabOrder, LabResult
from app.models.pharmacy import Medication, PharmacyInventory, Prescription, PrescriptionItem
from app.models.medical_record import MedicalRecord
from app.models.facility import Facility
from app.models.radiology import Radiology
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.models.patient_queue import PatientQueue
from app.models.alert import Alert
from app.models.audit_log import AuditLog

# Export all models
__all__ = [
    'BaseModel',
    'User',
    'Patient',
    'Appointment',
    'Invoice',
    'InvoiceItem', 
    'Payment',
    'InsuranceProvider',
    'InsuranceClaim',
    'LabTest',
    'LabOrder',
    'LabResult',
    'Medication',
    'PharmacyInventory',
    'Prescription',
    'PrescriptionItem',
    'MedicalRecord',
    'Facility',
    'Radiology',
    'Inventory',
    'Supplier',
    'PatientQueue',
    'Alert',
    'AuditLog',
]
