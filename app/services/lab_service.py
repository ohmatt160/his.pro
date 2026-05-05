from datetime import datetime
from app.models.lab import LabTest, LabOrder, LabResult
from app.extensions import db

class LabService:
    """Laboratory service class"""
    
    # ==================== Lab Tests ====================
    
    @staticmethod
    def create_lab_test(data):
        """Create a new lab test"""
        # Check if code already exists
        if LabTest.query.filter_by(code=data['code']).first():
            return None, "Lab test code already exists"
        
        test = LabTest(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            category=data.get('category'),
            unit=data.get('unit'),
            reference_range=data.get('reference_range'),
            price=data.get('price', 0)
        )
        test.save()
        return test, None
    
    @staticmethod
    def get_lab_test_by_id(test_id):
        """Get lab test by ID"""
        return LabTest.query.get(test_id)
    
    @staticmethod
    def get_all_lab_tests(active_only=True):
        """Get all lab tests"""
        query = LabTest.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(LabTest.name).all()
    
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
    def create_lab_order(data, ordered_by_id):
        """Create a new lab order"""
        order = LabOrder(
            patient_id=data['patient_id'],
            test_id=data['test_id'],
            ordered_by=ordered_by_id,
            priority=data.get('priority', 'ROUTINE'),
            notes=data.get('notes'),
            order_date=data.get('order_date', datetime.utcnow())
        )
        order.save()
        return order
    
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
        """Create or update lab result for an order"""
        # Check if result already exists
        result = LabResult.query.filter_by(order_id=order_id).first()
        
        if result:
            # Update existing result
            result.value = data.get('value')
            result.is_abnormal = data.get('is_abnormal', False)
            result.notes = data.get('notes')
            result.result_date = datetime.utcnow()
            result.save()
            return result
        
        # Create new result
        result = LabResult(
            order_id=order_id,
            value=data.get('value'),
            is_abnormal=data.get('is_abnormal', False),
            notes=data.get('notes'),
            result_date=datetime.utcnow()
        )
        result.save()
        
        # Update order status to completed
        LabService.update_lab_order_status(LabOrder.query.get(order_id), 'COMPLETED')
        
        return result
    
    @staticmethod
    def get_result_by_order(order_id):
        """Get lab result by order ID"""
        return LabResult.query.filter_by(order_id=order_id).first()
