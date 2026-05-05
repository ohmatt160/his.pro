import secrets
import string
from datetime import datetime, timedelta
from app.models.user import User
from app.extensions import db
from app.services.email_service import EmailService

class PasswordResetService:
    """Password reset service class"""
    
    # Store reset tokens in memory (in production, use Redis or database)
    reset_tokens = {}
    
    @staticmethod
    def generate_reset_token():
        """Generate a secure reset token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
    
    @staticmethod
    def request_password_reset(email):
        """Request password reset for user"""
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if not user:
            # Don't reveal if user exists or not
            return True, "If the email exists, a reset link has been sent"
        
        # Generate reset token
        token = PasswordResetService.generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store token
        PasswordResetService.reset_tokens[token] = {
            'user_id': user.id,
            'expires_at': expires_at
        }
        
        # Send password reset email
        EmailService.send_password_reset_email(email, token)
        
        return True, "If the email exists, a reset link has been sent"
    
    @staticmethod
    def validate_reset_token(token):
        """Validate password reset token"""
        if token not in PasswordResetService.reset_tokens:
            return False, "Invalid or expired reset token"
        
        token_data = PasswordResetService.reset_tokens[token]
        
        if datetime.utcnow() > token_data['expires_at']:
            del PasswordResetService.reset_tokens[token]
            return False, "Reset token has expired"
        
        return True, "Token is valid"
    
    @staticmethod
    def reset_password(token, new_password):
        """Reset user password using token"""
        # Validate token
        valid, message = PasswordResetService.validate_reset_token(token)
        
        if not valid:
            return False, message
        
        # Get user
        token_data = PasswordResetService.reset_tokens[token]
        user = User.query.get(token_data['user_id'])
        
        if not user:
            del PasswordResetService.reset_tokens[token]
            return False, "User not found"
        
        # Validate password
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters"
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Remove used token
        del PasswordResetService.reset_tokens[token]
        
        return True, "Password reset successfully"
