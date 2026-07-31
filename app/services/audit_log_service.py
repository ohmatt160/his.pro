from datetime import datetime
import logging

from app.models.audit_log import AuditLog
from app.extensions import db

logger = logging.getLogger(__name__)


class AuditLogService:
    """Service for audit logging operations"""

    @staticmethod
    def _request_ip(request):
        if not request:
            return None

        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip() or None

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip() or None

        return request.client.host if request.client else None

    @staticmethod
    def _request_user_agent(request):
        if not request:
            return None
        return request.headers.get("user-agent")

    @staticmethod
    def log_action(
        user_id,
        action,
        resource_type=None,
        resource_id=None,
        details=None,
        ip_address=None,
        user_agent=None,
        facility_slug=None,
        request=None,
        commit=True,
        raise_on_error=False,
        session=None,
    ):
        """Log a user action"""
        session = session or db.session
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                facility_id=(
                    getattr(request.state, "tenant_id", None) if request else None
                ),
                facility_slug=facility_slug,
                details=details or {},
                ip_address=ip_address or AuditLogService._request_ip(request),
                user_agent=user_agent or AuditLogService._request_user_agent(request),
            )
            session.add(audit_log)
            if commit:
                session.commit()
            else:
                session.flush()
            if request:
                request.state.audit_log_id = str(audit_log.id)
                request.state.audit_action = str(action)
            return audit_log
        except Exception:
            session.rollback()
            logger.exception("Failed to persist audit action %s", action)
            if raise_on_error:
                raise
            return None

    @staticmethod
    def get_logs(
        page=1,
        per_page=50,
        user_id=None,
        action=None,
        resource_type=None,
        facility_slug=None,
        start_date=None,
        end_date=None,
        limit=None,
    ):
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
        if start_date:
            query = query.filter(AuditLog.created_at >= datetime.fromisoformat(str(start_date)))
        if end_date:
            query = query.filter(AuditLog.created_at <= datetime.fromisoformat(str(end_date)))

        query = query.order_by(AuditLog.created_at.desc())

        # Manual pagination for SQLAlchemy 2.0
        if limit is not None:
            per_page = limit
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
