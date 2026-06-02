"""
File Upload Service - FastAPI compatible
Converted from Flask-based service to framework-agnostic
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

# Use absolute path based on current file location
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # goes to workspace root


class FileUploadService:
    """File upload service class"""

    MAX_FILE_SIZE = 5 * 1024 * 1024
    IMAGE_SIGNATURES = {
        "png": (b"\x89PNG\r\n\x1a\n",),
        "jpg": (b"\xff\xd8\xff",),
        "jpeg": (b"\xff\xd8\xff",),
        "gif": (b"GIF87a", b"GIF89a"),
        "webp": (b"RIFF",),
    }

    # Default allowed extensions
    DEFAULT_ALLOWED_EXTENSIONS = {
        'images': {'png', 'jpg', 'jpeg', 'gif', 'webp'},
        'documents': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'},
        'all': {'png', 'jpg', 'jpeg', 'gif', 'webp'}
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
        unique_id = uuid.uuid4().hex
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{timestamp}_{unique_id}.{ext}"

    @staticmethod
    def get_upload_folder(folder='uploads'):
        """Get upload folder path"""
        try:
            folder = FileUploadService.sanitize_folder(folder)
        except ValueError as exc:
            return False, str(exc)
        upload_folder = BASE_DIR / 'app' / 'static' / folder
        upload_folder.mkdir(parents=True, exist_ok=True)
        return str(upload_folder)

    @staticmethod
    def sanitize_folder(folder='uploads'):
        folder = (folder or 'uploads').strip().replace('\\', '/')
        parts = [part for part in folder.split('/') if part]
        if any(part in {'.', '..'} for part in parts):
            raise ValueError("Invalid upload folder")
        safe = [part for part in parts if part.replace('-', '').replace('_', '').isalnum()]
        return '/'.join(safe) if safe else 'uploads'

    @staticmethod
    def _extension(filename):
        return filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else ''

    @staticmethod
    def _looks_like_image(ext, content):
        signatures = FileUploadService.IMAGE_SIGNATURES.get(ext)
        if not signatures:
            return False
        if ext == "webp":
            return content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        return any(content.startswith(signature) for signature in signatures)

    @staticmethod
    def scan_for_malware(content):
        """Hook for malware scanning; detects EICAR locally and can require a scanner in prod."""
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            return False, "Malware signature detected"

        if os.getenv("MALWARE_SCAN_REQUIRED", "").lower() == "true":
            return False, "Malware scanner is not configured"

        return True, None

    @staticmethod
    def upload_file(file, folder='uploads', allowed_extensions=None):
        """Upload a file"""
        if not file or file.filename == '':
            return False, "No file provided"

        allowed_extensions = allowed_extensions or FileUploadService.DEFAULT_ALLOWED_EXTENSIONS['images']
        if not FileUploadService.allowed_file(file.filename, allowed_extensions):
            return False, "File type not allowed"

        try:
            folder = FileUploadService.sanitize_folder(folder)
        except ValueError as exc:
            return False, str(exc)
        ext = FileUploadService._extension(file.filename)
        content = file.file.read()
        if len(content) > FileUploadService.MAX_FILE_SIZE:
            return False, "File is too large"

        if not FileUploadService._looks_like_image(ext, content):
            return False, "File content is not a valid image"

        clean, scan_error = FileUploadService.scan_for_malware(content)
        if not clean:
            return False, scan_error

        # Generate unique filename
        filename = FileUploadService.generate_unique_filename(file.filename)

        # Get upload folder
        upload_folder = FileUploadService.get_upload_folder(folder)
        filepath = os.path.join(upload_folder, filename)

        # Save file
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
