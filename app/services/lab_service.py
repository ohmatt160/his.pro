from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.lab import LabTest, LabOrder, LabResult
from app.extensions import db
from app.utils.idempotency import verify_idempotent_replay

class LabService:
    """Laboratory service class"""
    
    # ==================== Lab Tests ====================
    
    @staticmethod
    def create_lab_test(data, facility_slug, facility_id=None):
        """Create a new lab test"""
        if LabTest.query.filter_by(
            code=data['code'],
            facility_slug=facility_slug,
        ).first():
            return None, "Lab test code already exists"
        
        test = LabTest(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            category=data.get('category'),
            unit=data.get('unit'),
            reference_range=data.get('reference_range'),
            price=data.get('price', 0),
            facility_id=facility_id,
            facility_slug=facility_slug,
        )
        test.save()
        return test, None
    
    @staticmethod
    def get_lab_test_by_id(test_id, facility_slug=None):
        """Get lab test by ID"""
        query = LabTest.query.filter_by(id=test_id)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        return query.first()
    
    @staticmethod
    def get_all_lab_tests(facility_slug, active_only=True, page=1, per_page=100):
        """Get a bounded tenant-owned lab test catalog."""
        query = LabTest.query.filter_by(facility_slug=facility_slug)
        if active_only:
            query = query.filter_by(is_active=True)
        return (
            query.order_by(LabTest.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
    
    @staticmethod
    def update_lab_test(test, data):
        """Update lab test"""
        for key, value in data.items():
            if hasattr(test, key) and value is not None:
                setattr(test, key, value)
        test.save()
        return test
    
    # ==================== Lab Orders ====================
    
    @staticmethod
    def create_lab_order(data, ordered_by_id, idempotency_key=None, payload_hash=None):
        """Create a new lab order"""
        existing = LabOrder.query.filter_by(
            facility_slug=data.get('facility_slug'),
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return verify_idempotent_replay(existing, payload_hash), False

        order_date = data.get('order_date') or datetime.utcnow()
        if isinstance(order_date, str):
            order_date = datetime.fromisoformat(order_date)

        order = LabOrder(
            patient_id=data['patient_id'],
            test_id=data['test_id'],
            facility_id=data.get('facility_id'),
            facility_slug=data.get('facility_slug'),
            branch_id=data.get('branch_id') or data.get('department_id'),
            department_id=data.get('department_id') or data.get('branch_id'),
            ordered_by=ordered_by_id,
            priority=data.get('priority', 'ROUTINE'),
            notes=data.get('notes'),
            idempotency_key=idempotency_key,
            idempotency_payload_hash=payload_hash,
            order_date=order_date
        )
        try:
            order.save()
            return order, True
        except IntegrityError:
            db.session.rollback()
            existing = LabOrder.query.filter_by(
                facility_slug=data.get('facility_slug'),
                idempotency_key=idempotency_key,
            ).first()
            if not existing:
                raise
            return verify_idempotent_replay(existing, payload_hash), False
    
    @staticmethod
    def get_lab_order_by_id(order_id):
        """Get lab order by ID"""
        return LabOrder.query.get(order_id)
    
    @staticmethod
    def get_lab_orders_by_patient(patient_id, facility_slug):
        """Get all lab orders for a patient"""
        return LabOrder.query.filter_by(
            patient_id=patient_id, 
            facility_slug=facility_slug
        ).order_by(LabOrder.order_date.desc()).all()
    
    @staticmethod
    def get_lab_orders_by_status(status, facility_slug):
        """Get lab orders by status"""
        return LabOrder.query.filter_by(
            status=status, 
            facility_slug=facility_slug
        ).order_by(LabOrder.order_date).all()
    
    @staticmethod
    def update_lab_order_status(order, status):
        """Update lab order status"""
        order.status = status
        
        if status == 'COLLECTED':
            order.collection_date = datetime.utcnow()
        elif status == 'COMPLETED':
            order.completed_date = datetime.utcnow()
        
        order.save()
        return order
    
    # ==================== Lab Results ====================
    
    @staticmethod
    def create_lab_result(order_id, data):
        """Create one result atomically and complete its order."""
        order_query = LabOrder.query.filter_by(id=order_id)
        if db.session.bind and db.session.bind.dialect.name == "postgresql":
            order_query = order_query.with_for_update()
        order = order_query.first()
        if not order:
            return None, False
        existing = LabResult.query.filter_by(order_id=order_id).first()
        if existing:
            return existing, False

        result = LabResult(
            order_id=order_id,
            value=data.get('value'),
            is_abnormal=data.get('is_abnormal', False),
            notes=data.get('notes'),
            result_date=datetime.utcnow()
        )
        try:
            db.session.add(result)
            order.status = "COMPLETED"
            order.completed_date = datetime.utcnow()
            db.session.add(order)
            db.session.commit()
            db.session.refresh(result)
            return result, True
        except IntegrityError:
            db.session.rollback()
            existing = LabResult.query.filter_by(order_id=order_id).first()
            if existing:
                return existing, False
            raise
    
    @staticmethod
    def get_result_by_order(order_id):
        """Get lab result by order ID"""
        return LabResult.query.filter_by(order_id=order_id).first()
