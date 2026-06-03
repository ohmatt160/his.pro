from datetime import datetime

from app.extensions import db_session
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.utils.validators import Validators


class PatientNotificationService:
    """Create patient portal/SMS notifications without external provider coupling."""

    @staticmethod
    def create(
        *,
        facility_slug: str,
        patient: Patient,
        notification_type: str,
        title: str,
        message: str,
        source_type: str | None = None,
        source_id: str | None = None,
        metadata: dict | None = None,
        channels: list[str] | None = None,
    ) -> list[PatientNotification]:
        created = []
        channels = channels or ["PORTAL", "SMS"]
        for channel in channels:
            normalized_channel = channel.upper()
            status = "QUEUED"
            if normalized_channel == "SMS" and not patient.phone:
                status = "SUPPRESSED"

            notification = PatientNotification(
                facility_slug=facility_slug,
                patient_id=patient.id,
                notification_type=notification_type,
                channel=normalized_channel,
                title=Validators.sanitize_string(title),
                message=Validators.sanitize_string(message),
                recipient_phone=patient.phone,
                recipient_email=patient.email,
                status=status,
                source_type=source_type,
                source_id=source_id,
                metadata_json=metadata or {},
            )
            db_session.add(notification)
            created.append(notification)
        db_session.flush()
        return created

    @staticmethod
    def mark_sent(notification: PatientNotification, provider_message_id: str | None = None) -> PatientNotification:
        metadata = dict(notification.metadata_json or {})
        if provider_message_id:
            metadata["provider_message_id"] = Validators.sanitize_string(provider_message_id)
        notification.metadata_json = metadata
        notification.status = "SENT"
        notification.sent_at = datetime.utcnow()
        db_session.add(notification)
        db_session.flush()
        return notification

    @staticmethod
    def mark_read(notification: PatientNotification) -> PatientNotification:
        notification.status = "READ"
        notification.read_at = datetime.utcnow()
        db_session.add(notification)
        db_session.flush()
        return notification

