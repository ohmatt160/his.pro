"""
Logging configuration for HIS.Pro Backend
"""

import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(app):
    """
    Setup logging configuration for the Flask application
    """
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging level based on environment
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'hispro.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # File handler for errors only
    error_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    
    # File handler for access logs
    access_file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'access.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    access_file_handler.setLevel(logging.INFO)
    access_file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    
    # Configure SQLAlchemy logger
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.WARNING)
    sqlalchemy_logger.addHandler(file_handler)
    
    # Configure Werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.addHandler(access_file_handler)
    
    # Log startup message
    app.logger.info(f'HIS.Pro Backend started at {datetime.now()}')
    app.logger.info(f'Log level: {logging.getLevelName(log_level)}')
    app.logger.info(f'Log directory: {log_dir}')
    
    return app.logger


class RequestFormatter(logging.Formatter):
    """
    Custom formatter that includes request information
    """
    
    def format(self, record):
        # Add request context if available
        try:
            from flask import request
            if request:
                record.url = request.url
                record.method = request.method
                record.remote_addr = request.remote_addr
            else:
                record.url = None
                record.method = None
                record.remote_addr = None
        except:
            record.url = None
            record.method = None
            record.remote_addr = None
        
        return super().format(record)


def log_request_response(app):
    """
    Log all requests and responses
    """
    
    @app.before_request
    def log_request_info():
        from flask import request
        app.logger.info(f'Request: {request.method} {request.url}')
        app.logger.debug(f'Headers: {dict(request.headers)}')
        app.logger.debug(f'Body: {request.get_data()}')
    
    @app.after_request
    def log_response_info(response):
        app.logger.info(f'Response: {response.status_code}')
        app.logger.debug(f'Response headers: {dict(response.headers)}')
        return response
    
    @app.errorhandler(Exception)
    def log_exception(error):
        app.logger.error(f'Exception: {error}', exc_info=True)
        raise error
