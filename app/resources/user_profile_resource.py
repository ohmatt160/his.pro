from flask_restx import Namespace, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.services.user_profile_service import UserProfileService
from app.schemas.user_schema import UserSchema
from app.utils.decorators import role_required

user_profile_ns = Namespace('users', description='User profile management operations')

# Swagger models
update_profile_model = user_profile_ns.model('UpdateProfile', {
    'first_name': fields.String(),
    'last_name': fields.String(),
    'email': fields.String(),
    'phone': fields.String()
})

change_password_model = user_profile_ns.model('ChangePassword', {
    'current_password': fields.String(required=True),
    'new_password': fields.String(required=True)
})


class UserProfileResource(BaseResource):
    """Resource for user profile operations"""
    
    @jwt_required()
    def get(self):
        """Get current user profile"""
        current_user_id = get_jwt_identity()
        print(f"[UserProfile] Getting profile for user_id: {current_user_id}")
        user = UserProfileService.get_user_by_id(current_user_id)
        
        if not user:
            print(f"[UserProfile] User not found for id: {current_user_id}")
            return self.handle_error("User not found", 404)
        
        print(f"[UserProfile] Found user: {user.username}, email: {user.email}, first_name: {user.first_name}, last_name: {user.last_name}, facility_slug: {user.facility_slug}")
        
        schema = UserSchema()
        user_data = schema.dump(user)
        print(f"[UserProfile] Serialized user data: {user_data}")
        return self.handle_response(data=user_data)
    
    @jwt_required()
    @user_profile_ns.expect(update_profile_model)
    def put(self):
        """Update current user profile"""
        current_user_id = get_jwt_identity()
        user = UserProfileService.get_user_by_id(current_user_id)
        
        if not user:
            return self.handle_error("User not found", 404)
        
        schema = UserSchema(partial=True)
        data = schema.load(user_profile_ns.payload)
        
        updated_user = UserProfileService.update_profile(user, data)
        
        return self.handle_response(
            data=schema.dump(updated_user),
            message="Profile updated successfully"
        )


class ChangePasswordResource(BaseResource):
    """Resource for password change"""
    
    @jwt_required()
    @user_profile_ns.expect(change_password_model)
    def post(self):
        """Change current user password"""
        current_user_id = get_jwt_identity()
        user = UserProfileService.get_user_by_id(current_user_id)
        
        if not user:
            return self.handle_error("User not found", 404)
        
        current_password = user_profile_ns.payload.get('current_password')
        new_password = user_profile_ns.payload.get('new_password')
        
        success, error = UserProfileService.change_password(
            user, current_password, new_password
        )
        
        if error:
            return self.handle_error(error, 400)
        
        return self.handle_response(message="Password changed successfully")


class UserListResource(BaseResource):
    """Resource for listing users (admin only)"""
    
    @role_required('ADMIN')
    def get(self):
        """Get all users for the current user's facility (admin only)"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role = request.args.get('role', None)
        
        # Get current user's facility for filtering
        current_user = self.get_current_user()
        if not current_user or not current_user.facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        result = UserProfileService.get_all_users(
            page=page, 
            per_page=per_page, 
            role=role,
            facility_slug=current_user.facility_slug  # Filter by facility
        )
        
        schema = UserSchema(many=True)
        return self.handle_response(data={
            'users': schema.dump(result['items']),
            'total': result['total'],
            'page': result['page'],
            'per_page': result['per_page'],
            'pages': result['pages']
        })


class UserResource(BaseResource):
    """Resource for individual user operations (admin only)"""
    
    @role_required('ADMIN')
    def get(self, user_id):
        """Get user by ID (admin only)"""
        user = UserProfileService.get_user_by_id(user_id)
        
        if not user:
            return self.handle_error("User not found", 404)
        
        schema = UserSchema()
        return self.handle_response(data=schema.dump(user))
    
    @role_required('ADMIN')
    @user_profile_ns.expect(update_profile_model)
    def put(self, user_id):
        """Update user (admin only)"""
        user = UserProfileService.get_user_by_id(user_id)
        
        if not user:
            return self.handle_error("User not found", 404)
        
        schema = UserSchema(partial=True)
        data = schema.load(user_profile_ns.payload)
        
        updated_user = UserProfileService.update_profile(user, data)
        
        return self.handle_response(
            data=schema.dump(updated_user),
            message="User updated successfully"
        )
    
    @role_required('ADMIN')
    def delete(self, user_id):
        """Deactivate user (admin only)"""
        user = UserProfileService.get_user_by_id(user_id)
        
        if not user:
            return self.handle_error("User not found", 404)
        
        UserProfileService.deactivate_user(user)
        
        return self.handle_response(message="User deactivated successfully")


# Register resources
user_profile_ns.add_resource(UserProfileResource, '/profile')
user_profile_ns.add_resource(ChangePasswordResource, '/profile/change-password')
user_profile_ns.add_resource(UserListResource, '')
user_profile_ns.add_resource(UserResource, '/<string:user_id>')
