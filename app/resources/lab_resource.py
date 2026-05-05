from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.lab_service import LabService
from app.schemas.lab_schema import LabTestSchema, LabOrderSchema, LabResultSchema
from app.utils.decorators import role_required

lab_ns = Namespace('laboratory', description='Laboratory management operations')

# Swagger models
lab_test_model = lab_ns.model('LabTest', {
    'name': fields.String(required=True),
    'code': fields.String(required=True),
    'description': fields.String(),
    'category': fields.String(),
    'unit': fields.String(),
    'reference_range': fields.String(),
    'price': fields.Float()
})

lab_order_model = lab_ns.model('LabOrder', {
    'patient_id': fields.String(required=True),
    'test_id': fields.String(required=True),
    'priority': fields.String(),
    'notes': fields.String(),
    'order_date': fields.String()
})

lab_result_model = lab_ns.model('LabResult', {
    'value': fields.String(),
    'is_abnormal': fields.Boolean(),
    'notes': fields.String()
})


# ==================== Lab Tests ====================

class LabTestListResource(BaseResource):
    """Resource for listing and creating lab tests"""
    
    @role_required('ADMIN', 'LAB_TECH')
    def get(self):
        """Get all lab tests"""
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        tests = LabService.get_all_lab_tests(active_only=active_only)
        schema = LabTestSchema(many=True)
        return self.handle_response(data=schema.dump(tests))
    
    @role_required('ADMIN')
    @lab_ns.expect(lab_test_model)
    def post(self):
        """Create a new lab test"""
        schema = LabTestSchema()
        data = schema.load(lab_ns.payload)
        
        test, error = LabService.create_lab_test(data)
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(
            data=schema.dump(test),
            message="Lab test created successfully",
            status_code=201
        )


class LabTestResource(BaseResource):
    """Resource for individual lab test operations"""
    
    @role_required('ADMIN', 'LAB_TECH', 'DOCTOR')
    def get(self, test_id):
        """Get lab test by ID"""
        test = LabService.get_lab_test_by_id(test_id)
        
        if not test:
            return self.handle_error("Lab test not found", 404)
        
        schema = LabTestSchema()
        return self.handle_response(data=schema.dump(test))
    
    @role_required('ADMIN')
    @lab_ns.expect(lab_test_model)
    def put(self, test_id):
        """Update lab test"""
        test = LabService.get_lab_test_by_id(test_id)
        
        if not test:
            return self.handle_error("Lab test not found", 404)
        
        schema = LabTestSchema(partial=True)
        data = schema.load(lab_ns.payload)
        
        updated_test = LabService.update_lab_test(test, data)
        
        return self.handle_response(
            data=schema.dump(updated_test),
            message="Lab test updated successfully"
        )


# ==================== Lab Orders ====================

class LabOrderListResource(BaseResource):
    """Resource for listing and creating lab orders"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')
    def get(self):
        """Get lab orders (filter by patient_id or status)"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        patient_id = request.args.get('patient_id')
        status = request.args.get('status')
        
        schema = LabOrderSchema(many=True)
        
        if patient_id:
            # Verify patient belongs to facility
            from app.models.patient import Patient
            patient = Patient.query.filter_by(id=patient_id, facility_slug=facility_slug).first()
            if not patient:
                return self.handle_error("Patient not found", 404)
            orders = LabService.get_lab_orders_by_patient(patient_id, facility_slug)
        elif status:
            orders = LabService.get_lab_orders_by_status(status, facility_slug)
        else:
            return self.handle_error("Please provide patient_id or status filter", 400)
        
        return self.handle_response(data=schema.dump(orders))
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE')
    @lab_ns.expect(lab_order_model)
    def post(self):
        """Create a new lab order"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Verify patient belongs to facility
        patient_id = lab_ns.payload.get('patient_id')
        if patient_id:
            from app.models.patient import Patient
            patient = Patient.query.filter_by(id=patient_id, facility_slug=facility_slug).first()
            if not patient:
                return self.handle_error("Patient not found", 404)
        
        schema = LabOrderSchema()
        data = schema.load(lab_ns.payload)
        
        # Force facility_slug
        data['facility_slug'] = facility_slug
        
        current_user_id = get_jwt_identity()
        order = LabService.create_lab_order(data, current_user_id)
        
        return self.handle_response(
            data=schema.dump(order),
            message="Lab order created successfully",
            status_code=201
        )


class LabOrderResource(BaseResource):
    """Resource for individual lab order operations"""
    
    @role_required('ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH')
    def get(self, order_id):
        """Get lab order by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        order = LabService.get_lab_order_by_id(order_id)
        
        if not order:
            return self.handle_error("Lab order not found", 404)
        
        # Verify order belongs to user's facility
        if order.facility_slug != facility_slug:
            return self.handle_error("Lab order not found", 404)
        
        schema = LabOrderSchema()
        return self.handle_response(data=schema.dump(order))
    
    @role_required('ADMIN', 'LAB_TECH')
    def put(self, order_id):
        """Update lab order status"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        order = LabService.get_lab_order_by_id(order_id)
        
        if not order:
            return self.handle_error("Lab order not found", 404)
        
        # Verify order belongs to user's facility
        if order.facility_slug != facility_slug:
            return self.handle_error("Lab order not found", 404)
        
        status = request.json.get('status')
        
        if not status or status not in ['PENDING', 'COLLECTED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']:
            return self.handle_error("Valid status is required", 400)
        
        updated_order = LabService.update_lab_order_status(order, status)
        schema = LabOrderSchema()
        
        return self.handle_response(
            data=schema.dump(updated_order),
            message="Lab order status updated successfully"
        )


# ==================== Lab Results ====================

class LabResultResource(BaseResource):
    """Resource for lab results"""
    
    @role_required('ADMIN', 'LAB_TECH', 'DOCTOR')
    def get(self, order_id):
        """Get lab result for an order"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # First get the order to check facility
        order = LabService.get_lab_order_by_id(order_id)
        if not order:
            return self.handle_error("Lab order not found", 404)
        
        # Verify order belongs to user's facility
        if order.facility_slug != facility_slug:
            return self.handle_error("Lab result not found", 404)
        
        result = LabService.get_result_by_order(order_id)
        
        if not result:
            return self.handle_error("Lab result not found", 404)
        
        schema = LabResultSchema()
        return self.handle_response(data=schema.dump(result))
    
    @role_required('ADMIN', 'LAB_TECH')
    @lab_ns.expect(lab_result_model)
    def post(self, order_id):
        """Create or update lab result"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        order = LabService.get_lab_order_by_id(order_id)
        
        if not order:
            return self.handle_error("Lab order not found", 404)
        
        # Verify order belongs to user's facility
        if order.facility_slug != facility_slug:
            return self.handle_error("Lab order not found", 404)
        
        if order.status == 'COMPLETED':
            return self.handle_error("Lab order already completed", 400)
        
        schema = LabResultSchema()
        data = schema.load(lab_ns.payload)
        
        result = LabService.create_lab_result(order_id, data)
        
        return self.handle_response(
            data=schema.dump(result),
            message="Lab result saved successfully",
            status_code=201
        )


# Register resources
lab_ns.add_resource(LabTestListResource, '/tests')
lab_ns.add_resource(LabTestResource, '/tests/<string:test_id>')
lab_ns.add_resource(LabOrderListResource, '/orders')
lab_ns.add_resource(LabOrderResource, '/orders/<string:order_id>')
lab_ns.add_resource(LabResultResource, '/results/<string:order_id>')
