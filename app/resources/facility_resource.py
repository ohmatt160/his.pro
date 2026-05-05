from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.facility import Facility
from app.utils.decorators import role_required
from app.utils.validators import Validators
from app.utils.rate_limiter import rate_limit_by_ip, AUTH_RATE_LIMIT
from app.extensions import db

facility_ns = Namespace('facilities', description='Facility management operations')

# Swagger model
facility_model = facility_ns.model('Facility', {
    'name': fields.String(required=True),
    'type': fields.String(required=True),
    'country': fields.String(),
    'address': fields.String(),
    'phone': fields.String(),
    'email': fields.String(),
    'modules': fields.List(fields.String()),
    'settings': fields.Raw()
})

facility_update_model = facility_ns.model('FacilityUpdate', {
    'name': fields.String(),
    'type': fields.String(),
    'country': fields.String(),
    'address': fields.String(),
    'phone': fields.String(),
    'email': fields.String(),
    'settings': fields.Raw()
})

modules_model = facility_ns.model('FacilityModules', {
    'modules': fields.List(fields.String(), required=True)
})


class FacilityListResource(BaseResource):
    """Resource for listing and creating facilities"""
    
    # Override method_decorators to remove token requirement for facility lookup
    method_decorators = []
    
    # Allow public access to list facilities (for facility lookup on login page)
    @facility_ns.doc(security=None)
    def get(self):
        """Get paginated list of facilities - public endpoint"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', None)
        
        if per_page > 100:
            per_page = 100
        
        query = Facility.query.filter_by(is_active=True)
        
        if search:
            query = query.filter(Facility.name.ilike(f'%{search}%'))
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        facilities = pagination.items
        
        return self.handle_response(data={
            'facilities': [f.to_dict() for f in facilities],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    # Allow public access to create facility (for initial setup)
    @rate_limit_by_ip(AUTH_RATE_LIMIT)
    @facility_ns.doc(security=None)
    @facility_ns.expect(facility_model)
    def post(self):
        """Create a new facility - public endpoint for initial setup"""
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return self.handle_error("Facility name is required", 400)
        if not data.get('type'):
            return self.handle_error("Facility type is required", 400)
        
        # Validate facility type
        if data['type'] not in Facility.FACILITY_TYPES:
            return self.handle_error(f"Invalid facility type. Must be one of: {', '.join(Facility.FACILITY_TYPES)}", 400)
        
        # Check for duplicate slug
        slug = Validators.generate_slug(data['name'])
        existing = Facility.query.filter_by(slug=slug).first()
        if existing:
            return self.handle_error("A facility with similar name already exists", 400)
        
        # Create facility
        facility = Facility(
            name=Validators.sanitize_string(data['name']),
            type=data['type'],
            slug=slug,
            country=data.get('country', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            modules=data.get('modules', []),
            settings=data.get('settings', {})
        )
        
        db.session.add(facility)
        db.session.commit()
        
        return self.handle_response(
            data=facility.to_dict(),
            message="Facility created successfully",
            status_code=201
        )


class FacilityResource(BaseResource):
    """Resource for individual facility operations"""
    
    # Override method_decorators to remove token requirement for facility lookup
    method_decorators = []
    
    @facility_ns.doc(security=None)
    def get(self, slug):
        """Get facility by slug - public endpoint for facility lookup"""
        facility = Facility.query.filter_by(slug=slug, is_active=True).first()
        
        if not facility:
            return self.handle_error("Facility not found", 404)
        
        return self.handle_response(data=facility.to_dict())
    
    @role_required('ADMIN')
    @facility_ns.expect(facility_update_model)
    def put(self, slug):
        """Update facility"""
        facility = Facility.query.filter_by(slug=slug, is_active=True).first()
        
        if not facility:
            return self.handle_error("Facility not found", 404)
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data and data['name']:
            facility.name = Validators.sanitize_string(data['name'])
        if 'type' in data:
            facility.type = data['type']
        if 'country' in data:
            facility.country = Validators.sanitize_string(data.get('country', ''))
        if 'address' in data:
            facility.address = Validators.sanitize_string(data.get('address', ''))
        if 'phone' in data:
            facility.phone = Validators.sanitize_string(data.get('phone', ''))
        if 'email' in data:
            facility.email = Validators.sanitize_string(data.get('email', ''))
        if 'settings' in data:
            facility.settings = data['settings']
        
        db.session.commit()
        
        return self.handle_response(
            data=facility.to_dict(),
            message="Facility updated successfully"
        )
    
    @role_required('ADMIN')
    def delete(self, slug):
        """Deactivate facility (soft delete)"""
        facility = Facility.query.filter_by(slug=slug, is_active=True).first()
        
        if not facility:
            return self.handle_error("Facility not found", 404)
        
        # Check if facility has active users
        active_users = facility.users
        if any(u.is_active for u in active_users):
            return self.handle_error("Cannot deactivate facility with active users", 400)
        
        facility.is_active = False
        db.session.commit()
        
        return self.handle_response(message="Facility deactivated successfully")


class FacilityModulesResource(BaseResource):
    """Resource for managing facility modules"""
    
    @role_required('ADMIN')
    @facility_ns.expect(modules_model)
    def put(self, slug):
        """Update enabled modules for a facility"""
        facility = Facility.query.filter_by(slug=slug, is_active=True).first()
        
        if not facility:
            return self.handle_error("Facility not found", 404)
        
        data = request.get_json()
        modules = data.get('modules', [])
        
        # Validate modules
        valid_modules = Facility.AVAILABLE_MODULES
        for module in modules:
            if module not in valid_modules:
                return self.handle_error(f"Invalid module: {module}", 400)
        
        facility.modules = modules
        db.session.commit()
        
        return self.handle_response(
            data=facility.to_dict(),
            message="Facility modules updated successfully"
        )


# Register resources
facility_ns.add_resource(FacilityListResource, '')
facility_ns.add_resource(FacilityResource, '/<string:slug>')
facility_ns.add_resource(FacilityModulesResource, '/<string:slug>/modules')