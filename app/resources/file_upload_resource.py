import os
from flask_restx import Namespace, fields
from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.resources.base_resource import BaseResource
from app.services.file_upload_service import FileUploadService
from app.utils.decorators import role_required

file_upload_ns = Namespace('files', description='File upload operations')

# Swagger models
upload_response_model = file_upload_ns.model('UploadResponse', {
    'filename': fields.String(),
    'url': fields.String(),
    'size': fields.Integer()
})


class FileUploadResource(BaseResource):
    """Resource for file uploads"""
    
    @jwt_required()
    def post(self):
        """Upload a file"""
        if 'file' not in request.files:
            return self.handle_error("No file provided", 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return self.handle_error("No file selected", 400)
        
        # Get optional parameters
        folder = request.form.get('folder', 'uploads')
        allowed_extensions = request.form.get('allowed_extensions', None)
        
        if allowed_extensions:
            allowed_extensions = allowed_extensions.split(',')
        
        success, result = FileUploadService.upload_file(
            file, 
            folder=folder,
            allowed_extensions=allowed_extensions
        )
        
        if not success:
            return self.handle_error(result, 400)
        
        return self.handle_response(
            data=result,
            message="File uploaded successfully",
            status_code=201
        )


class FileListResource(BaseResource):
    """Resource for listing files"""
    
    @jwt_required()
    def get(self):
        """List uploaded files"""
        folder = request.args.get('folder', 'uploads')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = FileUploadService.list_files(folder=folder, page=page, per_page=per_page)
        
        return self.handle_response(data=result)


class FileResource(BaseResource):
    """Resource for individual file operations"""
    
    @jwt_required()
    def get(self, filename):
        """Get file info"""
        folder = request.args.get('folder', 'uploads')
        
        file_info = FileUploadService.get_file_info(filename, folder=folder)
        
        if not file_info:
            return self.handle_error("File not found", 404)
        
        return self.handle_response(data=file_info)
    
    @role_required('ADMIN')
    def delete(self, filename):
        """Delete a file"""
        folder = request.args.get('folder', 'uploads')
        
        success, message = FileUploadService.delete_file(filename, folder=folder)
        
        if not success:
            return self.handle_error(message, 400)
        
        return self.handle_response(message=message)


# Register resources
file_upload_ns.add_resource(FileUploadResource, '/upload')
file_upload_ns.add_resource(FileListResource, '')
file_upload_ns.add_resource(FileResource, '/<string:filename>')
