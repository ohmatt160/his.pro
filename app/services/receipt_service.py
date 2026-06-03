import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.extensions import db_session
from app.models.billing import Payment


MAX_RECEIPT_SIZE = 5 * 1024 * 1024
ALLOWED_RECEIPT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def receipt_storage_dir() -> Path:
    configured = os.getenv("RECEIPT_UPLOAD_DIR")
    if configured:
        path = Path(configured)
    else:
        path = Path(__file__).resolve().parents[1] / "private_uploads" / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def receipt_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")
    return receipt_storage_dir() / filename


class ReceiptService:
    @staticmethod
    async def attach_receipt(payment: Payment, file: UploadFile) -> Payment:
        content_type = (file.content_type or "").lower()
        extension = ALLOWED_RECEIPT_TYPES.get(content_type)
        if not extension:
            raise HTTPException(status_code=400, detail="Receipt must be a JPEG, PNG, or WebP image")

        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="Receipt file is empty")
        if len(data) > MAX_RECEIPT_SIZE:
            raise HTTPException(status_code=413, detail="Receipt must be 5 MB or smaller")

        filename = f"{secrets.token_urlsafe(24)}{extension}"
        target = receipt_path(filename)
        target.write_bytes(data)

        if payment.receipt_filename:
            old_path = receipt_path(payment.receipt_filename)
            if old_path.exists():
                old_path.unlink()

        payment.receipt_filename = filename
        payment.receipt_original_name = Path(file.filename or "receipt").name
        payment.receipt_content_type = content_type
        payment.receipt_size = len(data)
        payment.receipt_uploaded_at = datetime.utcnow()
        db_session.add(payment)
        db_session.commit()
        db_session.refresh(payment)
        return payment

    @staticmethod
    def get_receipt_file(payment: Payment) -> Path:
        if not payment.receipt_filename:
            raise HTTPException(status_code=404, detail="Receipt not found")

        path = receipt_path(payment.receipt_filename)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Receipt not found")
        return path
