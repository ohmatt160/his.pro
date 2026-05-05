from app.models.user import User
from app.extensions import db

class UserProfileService:
    """User profile service class"""
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_all_users(page=1, per_page=20, role=None, facility_slug=None):
        """Get paginated list of users, optionally filtered by facility"""
        query = User.query
        
        # Filter by facility if provided (multi-tenant)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        
        if role:
            query = query.filter_by(role=role)
        
        pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    
    @staticmethod
    def update_profile(user, data):
        """Update user profile"""
        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.save()
        return user
    
    @staticmethod
    def change_password(user, current_password, new_password):
        """Change user password"""
        if not user.check_password(current_password):
            return False, "Current password is incorrect"
        
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters"
        
        user.set_password(new_password)
        user.save()
        return True, None
    
    @staticmethod
    def deactivate_user(user):
        """Deactivate user account"""
        user.is_active = False
        user.save()
        return True
