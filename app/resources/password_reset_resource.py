from flask_restx import Namespace, fields
from flask import request
from app.resources.base_resource import BaseResource
from app.services.password_reset_service import PasswordResetService
from app.utils.decorators import token_required

password_reset_ns = Namespace('password-reset', description='Password reset operations')

# Swagger models
forgot_password_model = password_reset_ns.model('ForgotPassword', {
    'email': fields.String(required=True)
})

reset_password_model = password_reset_ns.model('ResetPassword', {
    'token': fields.String(required=True),
    'new_password': fields.String(required=True)
})


class ForgotPasswordResource(BaseResource):
    """Resource for forgot password"""
    
    @password_reset_ns.expect(forgot_password_model)
    def post(self):
        """Request password reset email"""
        email = password_reset_ns.payload.get('email')
        
        if not email:
            return self.handle_error("Email is required", 400)
        
        success, message = PasswordResetService.request_password_reset(email)
        
        if not success:
            return self.handle_error(message, 400)
        
        return self.handle_response(message=message)


class ResetPasswordResource(BaseResource):
    """Resource for resetting password"""
    
    @password_reset_ns.expect(reset_password_model)
    def post(self):
        """Reset password using token"""
        token = password_reset_ns.payload.get('token')
        new_password = password_reset_ns.payload.get('new_password')
        
        if not token or not new_password:
            return self.handle_error("Token and new password are required", 400)
        
        success, message = PasswordResetService.reset_password(token, new_password)
        
        if not success:
            return self.handle_error(message, 400)
        
        return self.handle_response(message=message)


class ValidateResetTokenResource(BaseResource):
    """Resource for validating reset token"""
    
    def get(self, token):
        """Validate password reset token"""
        valid, message = PasswordResetService.validate_reset_token(token)
        
        if not valid:
            return self.handle_error(message, 400)
        
        return self.handle_response(message=message)


# Register resources
password_reset_ns.add_resource(ForgotPasswordResource, '/forgot')
password_reset_ns.add_resource(ResetPasswordResource, '/reset')
password_reset_ns.add_resource(ValidateResetTokenResource, '/validate/<string:token>')
