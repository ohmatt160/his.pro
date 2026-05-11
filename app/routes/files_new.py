"""
File Upload Routes - FastAPI Version
Converted from Flask-RESTx file_upload_resource.py
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime
import logging

from app.utils.dependencies import role_required
from app.models.user import User
from app.services.file_upload_service import FileUploadService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


class MessageResponse(BaseModel):
    message: str


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form('uploads'),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """Upload a file"""
    success, result = FileUploadService.upload_file(file, folder=folder)

    if not success:
        raise HTTPException(status_code=400, detail=result)

    return {"message": "File uploaded successfully", **result}


@router.get("")
async def list_files(
    folder: str = Query('uploads'),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """List uploaded files"""
    result = FileUploadService.list_files(folder=folder, page=page, per_page=per_page)
    return result


@router.get("/{filename}")
async def get_file_info(
    filename: str,
    folder: str = Query('uploads'),
    current_user: User = Depends(role_required('ADMIN', 'DOCTOR', 'NURSE', 'RECEPTIONIST'))
):
    """Get file information"""
    file_info = FileUploadService.get_file_info(filename, folder=folder)

    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    return file_info


@router.delete("/{filename}", response_model=MessageResponse)
async def delete_file(
    filename: str,
    folder: str = Query('uploads'),
    current_user: User = Depends(role_required('ADMIN'))
):
    """Delete a file"""
    success, message = FileUploadService.delete_file(filename, folder=folder)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return MessageResponse(message=message)
