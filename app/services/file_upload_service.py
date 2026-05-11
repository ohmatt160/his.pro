"""
File Upload Service - FastAPI compatible
Converted from Flask-based service to framework-agnostic
"""

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from pathlib import Path

# Use absolute path based on current file location
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # goes to workspace root


class FileUploadService:
    """File upload service class"""

    # Default allowed extensions
    DEFAULT_ALLOWED_EXTENSIONS = {
        'images': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'documents': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'},
        'all': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'}
    }

    @staticmethod
    def allowed_file(filename, allowed_extensions=None):
        """Check if file extension is allowed"""
        if not filename:
            return False

        if '.' not in filename:
            return False

        ext = filename.rsplit('.', 1)[1].lower()

        if allowed_extensions:
            return ext in allowed_extensions

        return ext in FileUploadService.DEFAULT_ALLOWED_EXTENSIONS['all']

    @staticmethod
    def generate_unique_filename(filename):
        """Generate unique filename"""
        ext = filename.rsplit('.', 1)[1].lower()
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}.{ext}"

    @staticmethod
    def get_upload_folder(folder='uploads'):
        """Get upload folder path"""
        upload_folder = BASE_DIR / 'app' / 'static' / folder
        upload_folder.mkdir(parents=True, exist_ok=True)
        return str(upload_folder)

    @staticmethod
    def upload_file(file, folder='uploads', allowed_extensions=None):
        """Upload a file"""
        if not file or file.filename == '':
            return False, "No file provided"

        if not FileUploadService.allowed_file(file.filename, allowed_extensions):
            return False, "File type not allowed"

        # Generate unique filename
        filename = FileUploadService.generate_unique_filename(file.filename)

        # Get upload folder
        upload_folder = FileUploadService.get_upload_folder(folder)
        filepath = os.path.join(upload_folder, filename)

        # Save file
        content = file.read()
        with open(filepath, "wb") as buffer:
            buffer.write(content)

        # Get file size
        file_size = os.path.getsize(filepath)

        # Generate URL (static path)
        file_url = f"/static/{folder}/{filename}"

        return True, {
            'filename': filename,
            'original_filename': file.filename,
            'url': file_url,
            'size': file_size,
            'folder': folder,
            'uploaded_at': datetime.utcnow().isoformat()
        }

    @staticmethod
    def list_files(folder='uploads', page=1, per_page=20):
        """List uploaded files"""
        upload_folder = FileUploadService.get_upload_folder(folder)

        if not os.path.exists(upload_folder):
            return {
                'files': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }

        # Get all files
        all_files = []
        for fname in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, fname)
            if os.path.isfile(filepath):
                file_stat = os.stat(filepath)
                all_files.append({
                    'filename': fname,
                    'size': file_stat.st_size,
                    'modified_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })

        # Sort by modification time (newest first)
        all_files.sort(key=lambda x: x['modified_at'], reverse=True)

        # Paginate
        total = len(all_files)
        start = (page - 1) * per_page
        end = start + per_page
        files = all_files[start:end]

        return {
            'files': files,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }

    @staticmethod
    def get_file_info(filename, folder='uploads'):
        """Get file information"""
        upload_folder = FileUploadService.get_upload_folder(folder)
        filepath = os.path.join(upload_folder, filename)

        if not os.path.exists(filepath):
            return None

        file_stat = os.stat(filepath)

        return {
            'filename': filename,
            'size': file_stat.st_size,
            'modified_at': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'url': f"/static/{folder}/{filename}"
        }

    @staticmethod
    def delete_file(filename, folder='uploads'):
        """Delete a file"""
        upload_folder = FileUploadService.get_upload_folder(folder)
        filepath = os.path.join(upload_folder, filename)

        if not os.path.exists(filepath):
            return False, "File not found"

        try:
            os.remove(filepath)
            return True, "File deleted successfully"
        except Exception as e:
            return False, f"Error deleting file: {str(e)}"
