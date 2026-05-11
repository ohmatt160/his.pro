"""
File Upload Routes - FastAPI Version
Converted from Flask-RESTx file_upload_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.extensions import get_db
from app.utils.dependencies import get_current_user, role_required
from app.services.file_upload_service import FileUploadService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


# Pydantic Models
class UploadResponse(BaseModel):
    filename: str
    url: str
    size: int


class FileInfo(BaseModel):
    filename: str
    url: str
    size: int
    created_at: Optional[str] = None
    folder: Optional[str] = None


class FileListResponse(BaseModel):
    files: List[FileInfo]
    total: int
    page: int
    per_page: int


class MessageResponse(BaseModel):
    message: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
        file: UploadFile = File(...),
        folder: str = Form("uploads"),
        allowed_extensions: Optional[str] = Form(None),
        current_user: User = Depends(get_current_user)
):
    """Upload a file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Parse allowed extensions
    extensions_list = None
    if allowed_extensions:
        extensions_list = [ext.strip() for ext in allowed_extensions.split(',')]

    # Read file content
    file_content = await file.read()

    success, result = FileUploadService.upload_file(
        file,
        filename=file.filename,
        content=file_content,
        content_type=file.content_type,
        folder=folder,
        allowed_extensions=extensions_list
    )

    if not success:
        raise HTTPException(status_code=400, detail=result)

    return UploadResponse(**result)


@router.get("", response_model=FileListResponse)
async def list_files(
        folder: str = Query("uploads"),
        page: int = Query(1, ge=1),
        per_page: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user)
):
    """List uploaded files"""
    result = FileUploadService.list_files(folder=folder, page=page, per_page=per_page)
    return FileListResponse(**result)


@router.get("/{filename}", response_model=FileInfo)
async def get_file_info(
        filename: str,
        folder: str = Query("uploads"),
        current_user: User = Depends(get_current_user)
):
    """Get file info"""
    file_info = FileUploadService.get_file_info(filename, folder=folder)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    return FileInfo(**file_info)


@router.delete("/{filename}", response_model=MessageResponse)
async def delete_file(
        filename: str,
        folder: str = Query("uploads"),
        current_user: User = Depends(role_required('ADMIN'))
):
    """Delete a file"""
    success, message = FileUploadService.delete_file(filename, folder=folder)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return MessageResponse(message=message)