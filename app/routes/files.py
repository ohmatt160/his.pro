"""
File Upload Routes - FastAPI Version
Converted from Flask-RESTx file_upload_resource.py
"""

import logging
import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse

from app.schemas.users import MessageResponse
from app.utils.dependencies import role_required
from app.models.user import User
from app.services.file_upload_service import FileUploadService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


def _safe_folder(value: str) -> str:
    try:
        return FileUploadService.sanitize_folder(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid upload folder") from exc


def _tenant_folder(current_user: User, folder: str = "uploads") -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")

    safe_folder = _safe_folder(folder)
    branch_scope = current_user.branch_id or current_user.department_id or "facility"
    safe_branch_scope = _safe_folder(str(branch_scope))
    return f"tenants/{current_user.facility_slug}/{safe_branch_scope}/{safe_folder}"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form('uploads'),
    file_type: str = Form('images'),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """Upload a file"""
    if file_type not in FileUploadService.DEFAULT_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file category")
    allowed = FileUploadService.DEFAULT_ALLOWED_EXTENSIONS[file_type]
    safe_folder = _safe_folder(folder)
    success, result = FileUploadService.upload_file(
        file,
        folder=_tenant_folder(current_user, safe_folder),
        allowed_extensions=allowed,
    )

    if not success:
        raise HTTPException(status_code=400, detail=result)

    result["folder"] = safe_folder
    result["url"] = (
        f"/api/v1/files/content/{result['filename']}"
        f"?folder={quote(safe_folder, safe='')}"
    )
    return {"message": "File uploaded successfully", **result}


@router.get("")
async def list_files(
    folder: str = Query('uploads'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """List uploaded files"""
    result = FileUploadService.list_files(folder=_tenant_folder(current_user, folder), page=page, per_page=per_page)
    return result


@router.get("/content/{filename}")
async def download_file(
    filename: str,
    folder: str = Query('uploads'),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST')),
):
    """Download a private file after tenant and branch authorization."""
    tenant_folder = _tenant_folder(current_user, folder)
    file_info = FileUploadService.get_file_info(filename, folder=tenant_folder)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    upload_folder = FileUploadService.get_upload_folder(tenant_folder)
    if isinstance(upload_folder, tuple):
        raise HTTPException(status_code=404, detail="File not found")
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(
        f"{upload_folder}/{filename}",
        media_type=media_type,
        filename=filename,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{filename}")
async def get_file_info(
    filename: str,
    folder: str = Query('uploads'),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """Get file information"""
    file_info = FileUploadService.get_file_info(filename, folder=_tenant_folder(current_user, folder))

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    safe_folder = _safe_folder(folder)
    file_info["url"] = (
        f"/api/v1/files/content/{filename}"
        f"?folder={quote(safe_folder, safe='')}"
    )
    return file_info


@router.delete("/{filename}", response_model=MessageResponse)
async def delete_file(
    filename: str,
    folder: str = Query('uploads'),
    current_user: User = Depends(role_required('ADMIN'))
):
    """Delete a file"""
    success, message = FileUploadService.delete_file(filename, folder=_tenant_folder(current_user, folder))

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return MessageResponse(message=message)
