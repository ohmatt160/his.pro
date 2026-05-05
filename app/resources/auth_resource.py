from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from app.resources.base_resource import BaseResource
from app.services.auth_service import AuthService
from app.schemas.user_schema import UserSchema, LoginSchema
from app.utils.validators import Validators
from app.utils.rate_limiter import rate_limit_by_ip, AUTH_RATE_LIMIT

auth_ns = Namespace('auth', description='Authentication operations')

# Swagger models
register_model = auth_ns.model('Register', {
    'username': fields.String(required=True),
    'email': fields.String(required=True),
    'password': fields.String(required=True),
    'role': fields.String(required=True),
    'first_name': fields.String(),
    'last_name': fields.String(),
    'facility_slug': fields.String()  # Add facility_slug for initial setup
})

login_model = auth_ns.model('Login', {
    'username': fields.String(required=True),
    'password': fields.String(required=True)
})

class RegisterResource(BaseResource):
    """User registration resource"""
    
    # Override method_decorators to remove token requirement for registration
    method_decorators = []
    
    @auth_ns.expect(register_model)
    @auth_ns.doc(security=None)
    def post(self):
        """Register a new user"""
        try:
            schema = UserSchema()
            data = schema.load(auth_ns.payload)
            
            # Sanitize input fields
            data['username'] = Validators.sanitize_string(data.get('username', ''))
            data['email'] = Validators.sanitize_string(data.get('email', ''))
            if data.get('first_name'):
                data['first_name'] = Validators.sanitize_string(data['first_name'])
            if data.get('last_name'):
                data['last_name'] = Validators.sanitize_string(data['last_name'])
            
            print(f"[Register] Creating user with data: {data}")
            
            user, error = AuthService.register_user(data)
            
            if error:
                print(f"[Register] Error: {error}")
                return self.handle_error(error, 400)
            
            print(f"[Register] User created successfully: {user}")
            
            return self.handle_response(
                data=UserSchema().dump(user),
                message="User registered successfully",
                status_code=201
            )
        except Exception as e:
            print(f"[Register] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.handle_error(f"Registration failed: {str(e)}", 500)

class LoginResource(BaseResource):
    """User login resource"""
    
    # Override method_decorators to remove token requirement for login
    method_decorators = []
    
    @auth_ns.expect(login_model)
    @auth_ns.doc(security=None)
    def post(self):
        """Login and get access token"""
        try:
            schema = LoginSchema()
            data = schema.load(auth_ns.payload)
            
            # Sanitize input
            data['username'] = Validators.sanitize_string(data.get('username', ''))
            
            user, error = AuthService.authenticate_user(data['username'], data['password'])
            
            if error:
                return self.handle_error(error, 401)
            
            # Validate: user's facility must match the requested workspace
            # Get facility_slug from query param or check user's assigned facility
            requested_facility = request.args.get('facility_slug')
            print(f"[Login] Requested facility: {requested_facility}, User facility: {user.facility_slug}")
            
            if requested_facility and user.facility_slug != requested_facility:
                # Return generic error for security (don't reveal workspace association)
                print(f"[Login] User {user.username} (facility: {user.facility_slug}) tried to access workspace {requested_facility}")
                return self.handle_error("Invalid username or password", 401)
            
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            # Dump user data with all fields
            user_schema = UserSchema()
            user_data = user_schema.dump(user)
            print(f"[Login] Returning user data: {user_data}")
            
            return self.handle_response(
                data={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': user_data
                },
                message="Login successful"
            )
        except Exception as e:
            import traceback
            print(f"[Login] Exception: {str(e)}")
            traceback.print_exc()
            return self.handle_error(f"Login failed: {str(e)}", 500)

class RefreshResource(BaseResource):
    """Token refresh resource"""
    
    @jwt_required(refresh=True)
    def post(self):
        """Refresh access token"""
        current_user = get_jwt_identity()
        new_access_token = create_access_token(identity=current_user)
        return {'access_token': new_access_token}

class LogoutResource(BaseResource):
    """Logout resource"""
    
    @jwt_required()
    def post(self):
        """Logout user by adding token to blocklist"""
        from app import jwt_blocklist
        jti = get_jwt()['jti']
        jwt_blocklist.add(jti)
        return self.handle_response(message="Logout successful")

# Register resources with namespace
auth_ns.add_resource(RegisterResource, '/register')
auth_ns.add_resource(LoginResource, '/login')
auth_ns.add_resource(RefreshResource, '/refresh')
auth_ns.add_resource(LogoutResource, '/logout')
