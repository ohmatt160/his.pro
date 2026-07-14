from datetime import datetime

from app.extensions import db_session
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.services.ohmattos_client import ohmattos_client
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
            PatientNotificationService._send_via_ohmattos(notification, patient, title, message)
        db_session.flush()
        return created

    @staticmethod
    def _send_via_ohmattos(
        notification: PatientNotification,
        patient: Patient,
        title: str,
        message: str,
    ) -> None:
        if not ohmattos_client.feature_enabled("notifications") or notification.status != "QUEUED":
            return
        channel = (notification.channel or "").upper()
        if channel not in {"SMS", "EMAIL"}:
            return
        if channel == "SMS" and not patient.phone:
            return
        if channel == "EMAIL" and not patient.email:
            return

        result = ohmattos_client.send_notification(
            user_id=str(patient.id),
            channel_type=channel.lower(),
            content={
                "title": Validators.sanitize_string(title),
                "message": Validators.sanitize_string(message),
                "facility_slug": notification.facility_slug,
                "patient_id": str(patient.id),
                "recipient_phone": patient.phone if channel == "SMS" else None,
                "recipient_email": patient.email if channel == "EMAIL" else None,
                "source_type": notification.source_type,
                "source_id": notification.source_id,
            },
        )
        metadata = dict(notification.metadata_json or {})
        metadata["ohmattos_delivery"] = {
            "queued": bool(result.get("ok")),
            "message_id": (result.get("data") or {}).get("message_id") if result.get("ok") else None,
            "error": result.get("error") if not result.get("ok") else None,
        }
        notification.metadata_json = metadata

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
