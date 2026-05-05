from app.models.audit_log import AuditLog
from app.extensions import db
from flask import request

class AuditLogService:
    """Service for audit logging operations"""
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None):
        """Log a user action"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request else None
            )
            db.session.add(audit_log)
            db.session.commit()
            return audit_log
        except Exception as e:
            db.session.rollback()
            print(f"Error logging audit action: {e}")
            return None
    
    @staticmethod
    def get_logs(page=1, per_page=50, user_id=None, action=None, resource_type=None):
        """Get audit logs with filtering"""
        query = AuditLog.query
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        query = query.order_by(AuditLog.created_at.desc())
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_log_by_id(log_id):
        """Get a specific audit log by ID"""
        return AuditLog.query.get(log_id)
    
    @staticmethod
    def get_user_logs(user_id, page=1, per_page=50):
        """Get audit logs for a specific user"""
        return AuditLog.query.filter_by(user_id=user_id).order_by(
            AuditLog.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
