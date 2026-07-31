import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.extensions import db_session
from app.models.billing import Payment
from app.services.file_upload_service import FileUploadService


MAX_RECEIPT_SIZE = int(os.getenv("MAX_RECEIPT_BYTES", str(5 * 1024 * 1024)))
ALLOWED_RECEIPT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _payment_tenant(payment: Payment) -> str:
    invoice = payment.invoice
    tenant = str(
        getattr(invoice, "facility_id", None)
        or getattr(invoice, "facility_slug", None)
        or ""
    )
    if not tenant or not tenant.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Payment tenant is invalid")
    return tenant


def receipt_storage_dir(payment: Payment) -> Path:
    configured = os.getenv("RECEIPT_UPLOAD_DIR")
    if configured:
        base = Path(configured)
    else:
        base = Path(__file__).resolve().parents[1] / "private_uploads" / "receipts"
    path = (base / _payment_tenant(payment)).resolve()
    if base.resolve() not in path.parents:
        raise HTTPException(status_code=400, detail="Payment tenant is invalid")
    path.mkdir(parents=True, exist_ok=True)
    return path


def receipt_path(payment: Payment, filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")
    return receipt_storage_dir(payment) / filename


def legacy_receipt_path(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid receipt filename")
    configured = os.getenv("RECEIPT_UPLOAD_DIR")
    base = Path(configured) if configured else Path(__file__).resolve().parents[1] / "private_uploads" / "receipts"
    return base.resolve() / filename


class ReceiptService:
    @staticmethod
    async def attach_receipt(payment: Payment, file: UploadFile) -> Payment:
        content_type = (file.content_type or "").lower()
        extension = ALLOWED_RECEIPT_TYPES.get(content_type)
        if not extension:
            raise HTTPException(status_code=400, detail="Receipt must be a JPEG, PNG, or WebP image")

        data = await file.read(MAX_RECEIPT_SIZE + 1)
        if not data:
            raise HTTPException(status_code=400, detail="Receipt file is empty")
        if len(data) > MAX_RECEIPT_SIZE:
            raise HTTPException(status_code=413, detail="Receipt must be 5 MB or smaller")
        if not FileUploadService._content_matches_extension(extension.lstrip("."), data):
            raise HTTPException(status_code=400, detail="Receipt content does not match its file type")
        clean, scan_error = FileUploadService.scan_for_malware(data)
        if not clean:
            raise HTTPException(status_code=400, detail=scan_error)

        filename = f"{secrets.token_urlsafe(24)}{extension}"
        target = receipt_path(payment, filename)
        target.write_bytes(data)

        old_filename = payment.receipt_filename

        payment.receipt_filename = filename
        payment.receipt_original_name = Path(file.filename or "receipt").name
        payment.receipt_content_type = content_type
        payment.receipt_size = len(data)
        payment.receipt_uploaded_at = datetime.utcnow()
        try:
            db_session.add(payment)
            db_session.commit()
            db_session.refresh(payment)
        except Exception:
            db_session.rollback()
            target.unlink(missing_ok=True)
            raise

        if old_filename:
            old_path = receipt_path(payment, old_filename)
            if old_path.exists():
                old_path.unlink()
            else:
                legacy_receipt_path(old_filename).unlink(missing_ok=True)
        return payment

    @staticmethod
    def get_receipt_file(payment: Payment) -> Path:
        if not payment.receipt_filename:
            raise HTTPException(status_code=404, detail="Receipt not found")

        path = receipt_path(payment, payment.receipt_filename)
        if not path.exists():
            path = legacy_receipt_path(payment.receipt_filename)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Receipt not found")
        return path
