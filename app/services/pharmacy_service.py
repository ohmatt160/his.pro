from datetime import datetime
from app.models.pharmacy import Medication, PharmacyInventory, Prescription, PrescriptionItem
from app.extensions import db

class PharmacyService:
    """Pharmacy service class"""
    
    # ==================== Medications ====================
    
    @staticmethod
    def create_medication(data):
        """Create a new medication"""
        if Medication.query.filter_by(code=data['code']).first():
            return None, "Medication code already exists"
        
        medication = Medication(
            name=data['name'],
            code=data['code'],
            generic_name=data.get('generic_name'),
            description=data.get('description'),
            category=data.get('category'),
            unit=data.get('unit'),
            strength=data.get('strength'),
            price=data.get('price', 0),
            reorder_level=data.get('reorder_level', 10)
        )
        medication.save()
        return medication, None
    
    @staticmethod
    def get_all_medications(facility_slug=None, active_only=True):
        """Get all medications, optionally filtered by facility"""
        query = Medication.query
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Medication.name).all()

    @staticmethod
    def get_medication_by_id(medication_id):
        """Get medication by ID"""
        return Medication.query.get(medication_id)
    
    @staticmethod
    def get_all_medications(active_only=True):
        """Get all medications"""
        query = Medication.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Medication.name).all()
    
    @staticmethod
    def update_medication(medication, data):
        """Update medication"""
        for key, value in data.items():
            if hasattr(medication, key) and value is not None:
                setattr(medication, key, value)
        medication.save()
        return medication
    
    # ==================== Inventory ====================

    @staticmethod
    def add_inventory(medication_id, facility_slug, data):
        """Add inventory for a medication"""
        # Verify medication belongs to facility
        medication = Medication.query.filter_by(id=medication_id, facility_slug=facility_slug).first()
        if not medication:
            return None, "Medication not found in this facility"

        # Check if inventory exists
        inventory = PharmacyInventory.query.filter_by(medication_id=medication_id).first()

        if inventory:
            # Update existing inventory
            inventory.quantity += data.get('quantity', 0)
            inventory.expiry_date = data.get('expiry_date', inventory.expiry_date)
            inventory.batch_number = data.get('batch_number', inventory.batch_number)
            inventory.location = data.get('location', inventory.location)
            inventory.save()
            return inventory, None

        # Create new inventory
        inventory = PharmacyInventory(
            medication_id=medication_id,
            quantity=data.get('quantity', 0),
            expiry_date=data.get('expiry_date'),
            batch_number=data.get('batch_number'),
            location=data.get('location')
        )
        inventory.save()
        return inventory, None

    @staticmethod
    def get_inventory(medication_id, facility_slug=None):
        """Get inventory for a medication, optionally filtered by facility"""
        query = PharmacyInventory.query.filter_by(medication_id=medication_id)
        if facility_slug:
            query = query.join(Medication, PharmacyInventory.medication_id == Medication.id).filter(Medication.facility_slug == facility_slug)
        return query.first()
    
    @staticmethod
    def check_stock(medication_id, quantity_needed):
        """Check if sufficient stock is available"""
        inventory = PharmacyInventory.query.filter_by(medication_id=medication_id).first()
        if not inventory or inventory.quantity < quantity_needed:
            return False
        return True
    
    @staticmethod
    def deduct_inventory(medication_id, quantity):
        """Deduct from inventory"""
        inventory = PharmacyInventory.query.filter_by(medication_id=medication_id).first()
        if inventory and inventory.quantity >= quantity:
            inventory.quantity -= quantity
            inventory.save()
            return True
        return False
    
    # ==================== Prescriptions ====================
    
    @staticmethod
    def create_prescription(data, prescribed_by_id):
        """Create a new prescription with items"""
        prescription = Prescription(
            patient_id=data['patient_id'],
            prescribed_by=prescribed_by_id,
            notes=data.get('notes'),
            prescription_date=datetime.utcnow()
        )
        prescription.save()
        
        # Add prescription items
        for item_data in data.get('items', []):
            item = PrescriptionItem(
                prescription_id=prescription.id,
                medication_id=item_data['medication_id'],
                quantity=item_data['quantity'],
                dosage=item_data.get('dosage'),
                instructions=item_data.get('instructions')
            )
            item.save()
        
        return prescription
    
    @staticmethod
    def get_prescription_by_id(prescription_id):
        """Get prescription by ID"""
        return Prescription.query.get(prescription_id)
    
    @staticmethod
    def get_prescriptions_by_patient(patient_id, facility_slug=None):
        """Get all prescriptions for a patient, optionally filtered by facility"""
        query = Prescription.query.filter_by(patient_id=patient_id)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        return query.order_by(Prescription.prescription_date.desc()).all()

    @staticmethod
    def get_pending_prescriptions(facility_slug=None):
        """Get all pending prescriptions, optionally filtered by facility"""
        query = Prescription.query.filter_by(status='PENDING')
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        return query.order_by(Prescription.prescription_date).all()
    
    @staticmethod
    def dispense_prescription(prescription_id, dispensed_by_id):
        """Dispense a prescription"""
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return None, "Prescription not found"
        
        if prescription.status != 'PENDING':
            return None, "Prescription cannot be dispensed"
        
        # Check and deduct inventory for each item
        for item in prescription.items:
            if not PharmacyService.check_stock(item.medication_id, item.quantity):
                return None, f"Insufficient stock for medication {item.medication_id}"
        
        # Deduct inventory
        for item in prescription.items:
            PharmacyService.deduct_inventory(item.medication_id, item.quantity)
            item.is_dispensed = True
            item.save()
        
        # Update prescription status
        prescription.status = 'DISPENSED'
        prescription.dispensed_by = dispensed_by_id
        prescription.dispensed_date = datetime.utcnow()
        prescription.save()
        
        return prescription, None
    
    @staticmethod
    def cancel_prescription(prescription_id):
        """Cancel a prescription"""
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return None, "Prescription not found"
        
        if prescription.status != 'PENDING':
            return None, "Only pending prescriptions can be cancelled"
        
        prescription.status = 'CANCELLED'
        prescription.save()
        
        return prescription, None
