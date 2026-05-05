from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.pharmacy_service import PharmacyService
from app.schemas.pharmacy_schema import MedicationSchema, PharmacyInventorySchema, PrescriptionSchema, PrescriptionItemSchema
from app.utils.decorators import role_required
from app.utils.validators import Validators

pharmacy_ns = Namespace('pharmacy', description='Pharmacy management operations')

# Swagger models
medication_model = pharmacy_ns.model('Medication', {
    'name': fields.String(required=True),
    'code': fields.String(required=True),
    'generic_name': fields.String(),
    'description': fields.String(),
    'category': fields.String(),
    'unit': fields.String(),
    'strength': fields.String(),
    'price': fields.Float(),
    'reorder_level': fields.Integer()
})

inventory_model = pharmacy_ns.model('Inventory', {
    'quantity': fields.Integer(required=True),
    'expiry_date': fields.String(),
    'batch_number': fields.String(),
    'location': fields.String()
})

prescription_item_model = pharmacy_ns.model('PrescriptionItem', {
    'medication_id': fields.String(required=True),
    'quantity': fields.Integer(required=True),
    'dosage': fields.String(),
    'instructions': fields.String()
})

prescription_model = pharmacy_ns.model('Prescription', {
    'patient_id': fields.String(required=True),
    'items': fields.List(fields.Nested(prescription_item_model), required=True),
    'notes': fields.String()
})


# ==================== Medications ====================

class MedicationListResource(BaseResource):
    """Resource for listing and creating medications"""
    
    @role_required('ADMIN', 'PHARMACIST', 'DOCTOR')
    def get(self):
        """Get all medications for user's facility"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        medications = PharmacyService.get_all_medications(facility_slug=facility_slug, active_only=active_only)
        schema = MedicationSchema(many=True)
        return self.handle_response(data=schema.dump(medications))
    
    @role_required('ADMIN')
    @pharmacy_ns.expect(medication_model)
    def post(self):
        """Create a new medication"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = MedicationSchema()
        data = schema.load(pharmacy_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        medication, error = PharmacyService.create_medication(data)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(medication),
            message="Medication created successfully",
            status_code=201
        )


class MedicationResource(BaseResource):
    """Resource for individual medication operations"""
    
    @role_required('ADMIN', 'PHARMACIST', 'DOCTOR')
    def get(self, medication_id):
        """Get medication by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        medication = PharmacyService.get_medication_by_id(medication_id)
        
        if not medication:
            return self.handle_error("Medication not found", 404)
        
        # Verify medication belongs to user's facility
        if medication.facility_slug != facility_slug:
            return self.handle_error("Medication not found", 404)
        
        schema = MedicationSchema()
        return self.handle_response(data=schema.dump(medication))
    
    @role_required('ADMIN')
    @pharmacy_ns.expect(medication_model)
    def put(self, medication_id):
        """Update medication"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        medication = PharmacyService.get_medication_by_id(medication_id)
        
        if not medication:
            return self.handle_error("Medication not found", 404)
        
        # Verify medication belongs to user's facility
        if medication.facility_slug != facility_slug:
            return self.handle_error("Medication not found", 404)
        
        schema = MedicationSchema(partial=True)
        data = schema.load(pharmacy_ns.payload)
        
        updated_medication = PharmacyService.update_medication(medication, data)
        
        return self.handle_response(
            data=schema.dump(updated_medication),
            message="Medication updated successfully"
        )


# ==================== Inventory ====================

class InventoryResource(BaseResource):
    """Resource for inventory operations"""
    
    @role_required('ADMIN', 'PHARMACIST')
    def get(self, medication_id):
        """Get inventory for a medication"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        inventory = PharmacyService.get_inventory(medication_id, facility_slug)
        
        if not inventory:
            return self.handle_error("Inventory not found", 404)
        
        schema = PharmacyInventorySchema()
        return self.handle_response(data=schema.dump(inventory))
    
    @role_required('ADMIN', 'PHARMACIST')
    @pharmacy_ns.expect(inventory_model)
    def post(self, medication_id):
        """Add inventory for a medication"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = PharmacyInventorySchema()
        data = schema.load(pharmacy_ns.payload)
        
        inventory, error = PharmacyService.add_inventory(medication_id, facility_slug, data)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(inventory),
            message="Inventory added successfully",
            status_code=201
        )


# ==================== Prescriptions ====================

class PrescriptionListResource(BaseResource):
    """Resource for listing and creating prescriptions"""
    
    @role_required('ADMIN', 'DOCTOR', 'PHARMACIST')
    def get(self):
        """Get prescriptions for user's facility"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        status = request.args.get('status')
        
        # Always filter by facility
        if patient_id:
            # Verify patient belongs to facility
            from app.models.patient import Patient
            patient = Patient.query.filter_by(id=patient_id, facility_slug=facility_slug).first()
            if not patient:
                return self.handle_error("Patient not found", 404)
            prescriptions = PharmacyService.get_prescriptions_by_patient(patient_id, facility_slug)
        elif status == 'PENDING':
            prescriptions = PharmacyService.get_pending_prescriptions(facility_slug)
        else:
            # Get all prescriptions for facility
            from app.models.pharmacy import Prescription
            prescriptions = Prescription.query.filter_by(facility_slug=facility_slug).order_by(Prescription.created_at.desc()).all()
        
        schema = PrescriptionSchema(many=True)
        return self.handle_response(data=schema.dump(prescriptions))
    
    @role_required('ADMIN', 'DOCTOR')
    @pharmacy_ns.expect(prescription_model)
    def post(self):
        """Create a new prescription"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        schema = PrescriptionSchema()
        data = schema.load(pharmacy_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        current_user_id = get_jwt_identity()
        prescription = PharmacyService.create_prescription(data, current_user_id)
        
        return self.handle_response(
            data=schema.dump(prescription),
            message="Prescription created successfully",
            status_code=201
        )


class PrescriptionResource(BaseResource):
    """Resource for individual prescription operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'PHARMACIST')
    def get(self, prescription_id):
        """Get prescription by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        prescription = PharmacyService.get_prescription_by_id(prescription_id)
        
        if not prescription:
            return self.handle_error("Prescription not found", 404)
        
        # Verify prescription belongs to user's facility
        if prescription.facility_slug != facility_slug:
            return self.handle_error("Prescription not found", 404)
        
        schema = PrescriptionSchema()
        return self.handle_response(data=schema.dump(prescription))
    
    @role_required('ADMIN', 'PHARMACIST')
    def post(self, prescription_id):
        """Dispense a prescription"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        prescription = PharmacyService.get_prescription_by_id(prescription_id)
        
        if not prescription:
            return self.handle_error("Prescription not found", 404)
        
        # Verify prescription belongs to user's facility
        if prescription.facility_slug != facility_slug:
            return self.handle_error("Prescription not found", 404)
        
        current_user_id = get_jwt_identity()
        prescription, error = PharmacyService.dispense_prescription(prescription_id, current_user_id)
        
        if error:
            return self.handle_error(error, 400)
        
        schema = PrescriptionSchema()
        return self.handle_response(
            data=schema.dump(prescription),
            message="Prescription dispensed successfully"
        )
    
    @role_required('ADMIN', 'DOCTOR')
    def delete(self, prescription_id):
        """Cancel a prescription"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        prescription = PharmacyService.get_prescription_by_id(prescription_id)
        
        if not prescription:
            return self.handle_error("Prescription not found", 404)
        
        # Verify prescription belongs to user's facility
        if prescription.facility_slug != facility_slug:
            return self.handle_error("Prescription not found", 404)
        
        prescription, error = PharmacyService.cancel_prescription(prescription_id)
        
        if error:
            return self.handle_error(error, 400)
        
        schema = PrescriptionSchema()
        return self.handle_response(
            data=schema.dump(prescription),
            message="Prescription cancelled successfully"
        )


# Register resources
pharmacy_ns.add_resource(MedicationListResource, '/medications')
pharmacy_ns.add_resource(MedicationResource, '/medications/<string:medication_id>')
pharmacy_ns.add_resource(InventoryResource, '/inventory/<string:medication_id>')
pharmacy_ns.add_resource(PrescriptionListResource, '/prescriptions')
pharmacy_ns.add_resource(PrescriptionResource, '/prescriptions/<string:prescription_id>')
