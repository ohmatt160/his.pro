from app.models.user import User
from app.extensions import db

class AuthService:
    """Authentication service class"""
    
    @staticmethod
    def register_user(data):
        """Register a new user"""
        # Validate role
        allowed_roles = User.get_roles()
        if data.get('role') not in allowed_roles:
            return None, f"Invalid role. Allowed roles: {', '.join(allowed_roles)}"
        
        # Check if user exists
        if User.query.filter_by(username=data['username']).first():
            return None, "Username already exists"
        
        if User.query.filter_by(email=data['email']).first():
            return None, "Email already exists"
        
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            role=data['role'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            facility_slug=data.get('facility_slug')  # Assign facility if provided
        )
        user.set_password(data['password'])
        
        user.save()
        return user, None
    
    @staticmethod
    def authenticate_user(username, password):
        """Authenticate user credentials"""
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if not user:
            print(f"[AUTH] User not found: {username}")
            return None, "Invalid username or password"
        
        if not user.check_password(password):
            print(f"[AUTH] Password check failed for: {username}")
            return None, "Invalid username or password"
        
        print(f"[AUTH] Login successful for: {username}, role: {user.role}")
        return user, None
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
