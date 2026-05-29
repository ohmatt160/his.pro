from app.models.user import User
from app.extensions import db_session
from app.utils.validators import Validators

class AuthService:
    """Authentication service class"""
    
    @staticmethod
    def register_user(data, session=None):
        """Register a new user"""
        session = session or db_session
        data = dict(data)
        data['role'] = data.get('role', '').upper()

        # Validate role
        allowed_roles = User.get_roles()
        if data.get('role') not in allowed_roles:
            return None, f"Invalid role. Allowed roles: {', '.join(allowed_roles)}"
        
        # Check if user exists
        if session.query(User).filter_by(username=data['username']).first():
            return None, "Username already exists"
        
        if session.query(User).filter_by(email=data['email']).first():
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
        
        session.add(user)
        session.flush()
        return user, None
    
    @staticmethod
    def authenticate_user(username, password, session=None):
        """Authenticate user credentials"""
        session = session or db_session
        user = session.query(User).filter_by(username=username, is_active=True).first()
        
        if not user:
            print(f"[AUTH] User not found: {username}")
            return None, "Invalid username or password"
        
        if not user.check_password(password):
            print(f"[AUTH] Password check failed for: {username}")
            return None, "Invalid username or password"
        
        print(f"[AUTH] Login successful for: {username}, role: {user.role}")
        return user, None
    
    @staticmethod
    def get_user_by_id(user_id, session=None):
        """Get user by ID"""
        session = session or db_session
        return session.get(User, user_id)

    @staticmethod
    def change_password(user_id, current_password, new_password, session=None):
        """Change a user's password after verifying the current password."""
        session = session or db_session
        user = session.get(User, user_id)
        if not user or not user.is_active:
            return False, "User not found or inactive"

        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        is_valid, error = Validators.validate_password(new_password)
        if not is_valid:
            return False, error

        user.set_password(new_password)
        session.add(user)
        session.flush()
        return True, "Password changed successfully"
