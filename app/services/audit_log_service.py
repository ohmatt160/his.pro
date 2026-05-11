from app.models.audit_log import AuditLog
from app.extensions import db


class AuditLogService:
    """Service for audit logging operations"""

    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None, ip_address=None, user_agent=None):
        """Log a user action"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(audit_log)
            db.session.commit()
            return audit_log
        except Exception as e:
            db.session.rollback()
            print(f"Error logging audit action: {e}")
            return None

    @staticmethod
    def get_logs(page=1, per_page=50, user_id=None, action=None, resource_type=None, facility_slug=None):
        """Get audit logs with filtering"""
        query = AuditLog.query

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if facility_slug:
            query = query.filter(AuditLog.facility_slug == facility_slug)

        query = query.order_by(AuditLog.created_at.desc())

        # Manual pagination for SQLAlchemy 2.0
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page

        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }

    @staticmethod
    def get_log_by_id(log_id, facility_slug=None):
        """Get a specific audit log by ID"""
        query = AuditLog.query.filter_by(id=log_id)
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        return query.first()

    @staticmethod
    def get_user_logs(user_id, page=1, per_page=50):
        """Get audit logs for a specific user"""
        query = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }
