from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.audit_log_service import AuditLogService
from app.models.user import User

audit_log_ns = Namespace('audit-logs', description='Audit log operations')

audit_log_model = audit_log_ns.model('AuditLog', {
    'id': fields.String(description='Log ID'),
    'user_id': fields.String(description='User ID'),
    'action': fields.String(description='Action performed'),
    'resource_type': fields.String(description='Resource type'),
    'resource_id': fields.String(description='Resource ID'),
    'details': fields.Raw(description='Additional details'),
    'ip_address': fields.String(description='IP address'),
    'user_agent': fields.String(description='User agent'),
    'created_at': fields.DateTime(description='Creation timestamp')
})

pagination_model = audit_log_ns.model('Pagination', {
    'page': fields.Integer(description='Current page'),
    'per_page': fields.Integer(description='Items per page'),
    'total': fields.Integer(description='Total items'),
    'pages': fields.Integer(description='Total pages')
})

audit_log_list_model = audit_log_ns.model('AuditLogList', {
    'logs': fields.List(fields.Nested(audit_log_model)),
    'pagination': fields.Nested(pagination_model)
})


@audit_log_ns.route('/')
class AuditLogList(Resource):
    @jwt_required()
    @audit_log_ns.doc('list_audit_logs')
    @audit_log_ns.param('page', 'Page number', type=int, default=1)
    @audit_log_ns.param('per_page', 'Items per page', type=int, default=50)
    @audit_log_ns.param('user_id', 'Filter by user ID')
    @audit_log_ns.param('action', 'Filter by action')
    @audit_log_ns.param('resource_type', 'Filter by resource type')
    @audit_log_ns.marshal_with(audit_log_list_model)
    def get(self):
        """Get audit logs with filtering and pagination"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Only admins can view all audit logs
        if not user or user.role != 'admin':
            audit_log_ns.abort(403, 'Admin access required')
        
        page = audit_log_ns.payload.get('page', 1)
        per_page = audit_log_ns.payload.get('per_page', 50)
        user_id = audit_log_ns.payload.get('user_id')
        action = audit_log_ns.payload.get('action')
        resource_type = audit_log_ns.payload.get('resource_type')
        
        pagination = AuditLogService.get_logs(
            page=page,
            per_page=per_page,
            user_id=user_id,
            action=action,
            resource_type=resource_type
        )
        
        return {
            'logs': [log.to_dict() for log in pagination.items],
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }


@audit_log_ns.route('/<string:log_id>')
class AuditLogDetail(Resource):
    @jwt_required()
    @audit_log_ns.doc('get_audit_log')
    @audit_log_ns.marshal_with(audit_log_model)
    def get(self, log_id):
        """Get a specific audit log by ID"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Only admins can view audit logs
        if not user or user.role != 'admin':
            audit_log_ns.abort(403, 'Admin access required')
        
        log = AuditLogService.get_log_by_id(log_id)
        if not log:
            audit_log_ns.abort(404, 'Audit log not found')
        
        return log.to_dict()


@audit_log_ns.route('/user/<string:user_id>')
class UserAuditLogs(Resource):
    @jwt_required()
    @audit_log_ns.doc('get_user_audit_logs')
    @audit_log_ns.param('page', 'Page number', type=int, default=1)
    @audit_log_ns.param('per_page', 'Items per page', type=int, default=50)
    @audit_log_ns.marshal_with(audit_log_list_model)
    def get(self, user_id):
        """Get audit logs for a specific user"""
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        # Only admins can view other users' audit logs
        if not user or user.role != 'admin':
            audit_log_ns.abort(403, 'Admin access required')
        
        page = audit_log_ns.payload.get('page', 1)
        per_page = audit_log_ns.payload.get('per_page', 50)
        
        pagination = AuditLogService.get_user_logs(
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        
        return {
            'logs': [log.to_dict() for log in pagination.items],
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
