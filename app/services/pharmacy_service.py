from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from app.models.pharmacy import Medication, PharmacyInventory, Prescription, PrescriptionItem
from app.extensions import db, db_session
from app.utils.idempotency import verify_idempotent_replay

class PharmacyService:
    """Pharmacy service class"""

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.fromisoformat(str(value)).date()
    
    # ==================== Medications ====================
    
    @staticmethod
    def create_medication(data):
        """Create a new medication"""
        if Medication.query.filter_by(
            code=data['code'],
            facility_slug=data.get('facility_slug'),
        ).first():
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
            reorder_level=data.get('reorder_level', 10),
            facility_id=data.get('facility_id'),
            facility_slug=data.get('facility_slug')
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
    def update_medication(medication, data):
        """Update medication"""
        for key, value in data.items():
            if hasattr(medication, key) and value is not None:
                setattr(medication, key, value)
        medication.save()
        return medication
    
    # ==================== Inventory ====================

    @staticmethod
    def add_inventory(medication_id, facility_slug, data, *, commit=True):
        """Add inventory for a medication"""
        # Lock the medication row so two workers cannot both calculate stock
        # from the same starting quantity or race to create the inventory row.
        medication_query = Medication.query.filter_by(
            id=medication_id,
            facility_slug=facility_slug,
        )
        if db_session.bind and db_session.bind.dialect.name == "postgresql":
            medication_query = medication_query.with_for_update()
        medication = medication_query.first()
        if not medication:
            return None, "Medication not found in this facility"

        # Check if inventory exists
        inventory_query = PharmacyInventory.query.filter_by(medication_id=medication_id)
        if db_session.bind and db_session.bind.dialect.name == "postgresql":
            inventory_query = inventory_query.with_for_update()
        inventory = inventory_query.first()

        if inventory:
            inventory.quantity += data.get('quantity', 0)
            inventory.expiry_date = PharmacyService._parse_date(data.get('expiry_date')) or inventory.expiry_date
            inventory.batch_number = data.get('batch_number', inventory.batch_number)
            inventory.location = data.get('location', inventory.location)
            db_session.add(inventory)
            if commit:
                db_session.commit()
            else:
                db_session.flush()
            db_session.refresh(inventory)
            return inventory, None

        inventory = PharmacyInventory(
            medication_id=medication_id,
            quantity=data.get('quantity', 0),
            expiry_date=PharmacyService._parse_date(data.get('expiry_date')),
            batch_number=data.get('batch_number'),
            location=data.get('location')
        )
        db_session.add(inventory)
        try:
            if commit:
                db_session.commit()
            else:
                db_session.flush()
            db_session.refresh(inventory)
            return inventory, None
        except IntegrityError:
            if not commit:
                raise
            # Compatibility fallback for databases where row locking is not
            # available. Preserve the receipt against the winning row.
            db_session.rollback()
            inventory_query = PharmacyInventory.query.filter_by(
                medication_id=medication_id
            )
            if db_session.bind and db_session.bind.dialect.name == "postgresql":
                inventory_query = inventory_query.with_for_update()
            inventory = inventory_query.first()
            if not inventory:
                raise
            inventory.quantity += data.get('quantity', 0)
            inventory.expiry_date = (
                PharmacyService._parse_date(data.get('expiry_date'))
                or inventory.expiry_date
            )
            inventory.batch_number = data.get('batch_number', inventory.batch_number)
            inventory.location = data.get('location', inventory.location)
            db_session.commit()
            db_session.refresh(inventory)
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
    def create_prescription(data, prescribed_by_id, idempotency_key=None, payload_hash=None):
        """Create a new prescription with items"""
        existing = Prescription.query.filter_by(
            facility_slug=data.get('facility_slug'),
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return verify_idempotent_replay(existing, payload_hash), False

        prescription = Prescription(
            patient_id=data['patient_id'],
            prescribed_by=prescribed_by_id,
            facility_slug=data.get('facility_slug'),
            department_id=data.get('department_id'),
            branch_id=data.get('branch_id') or data.get('department_id'),
            notes=data.get('notes'),
            prescription_date=datetime.utcnow(),
            idempotency_key=idempotency_key,
            idempotency_payload_hash=payload_hash,
        )
        try:
            db_session.add(prescription)
            db_session.flush()
            for item_data in data.get('items', []):
                db_session.add(PrescriptionItem(
                    prescription_id=prescription.id,
                    medication_id=item_data['medication_id'],
                    quantity=item_data['quantity'],
                    dosage=item_data.get('dosage'),
                    instructions=item_data.get('instructions')
                ))
            db_session.commit()
        except IntegrityError:
            db_session.rollback()
            existing = Prescription.query.filter_by(
                facility_slug=data.get('facility_slug'),
                idempotency_key=idempotency_key,
            ).first()
            if not existing:
                raise
            return verify_idempotent_replay(existing, payload_hash), False
        except Exception:
            db_session.rollback()
            raise

        db_session.refresh(prescription)
        return prescription, True
    
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
    def dispense_prescription(prescription_id, dispensed_by_id, facility_slug=None):
        """Dispense a prescription"""
        query = Prescription.query.filter_by(id=prescription_id)
        if db_session.bind and db_session.bind.dialect.name == "postgresql":
            query = query.with_for_update()
        prescription = query.first()
        if not prescription:
            return None, "Prescription not found"

        if facility_slug and prescription.facility_slug != facility_slug:
            return None, "Prescription not found"
        
        if prescription.status != 'PENDING':
            return None, "Prescription cannot be dispensed"

        medication_ids = [item.medication_id for item in prescription.items]
        inventory_query = PharmacyInventory.query.filter(
            PharmacyInventory.medication_id.in_(medication_ids)
        )
        if db_session.bind and db_session.bind.dialect.name == "postgresql":
            inventory_query = inventory_query.with_for_update()
        inventory_by_medication = {
            row.medication_id: row for row in inventory_query.all()
        }
        for item in prescription.items:
            inventory = inventory_by_medication.get(item.medication_id)
            if not inventory or inventory.quantity < item.quantity:
                db_session.rollback()
                return None, f"Insufficient stock for medication {item.medication_id}"

        for item in prescription.items:
            inventory_by_medication[item.medication_id].quantity -= item.quantity
            item.is_dispensed = True

        prescription.status = 'DISPENSED'
        prescription.dispensed_by = dispensed_by_id
        prescription.dispensed_date = datetime.utcnow()
        db_session.commit()
        db_session.refresh(prescription)
        return prescription, None
    
    @staticmethod
    def cancel_prescription(prescription_id, facility_slug=None):
        """Cancel a prescription"""
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return None, "Prescription not found"

        if facility_slug and prescription.facility_slug != facility_slug:
            return None, "Prescription not found"
        
        if prescription.status != 'PENDING':
            return None, "Only pending prescriptions can be cancelled"
        
        prescription.status = 'CANCELLED'
        prescription.save()
        
        return prescription, None
