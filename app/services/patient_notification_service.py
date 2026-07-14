import logging
import os
import uuid
from datetime import datetime

from app.extensions import db_session
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.services.ohmattos_client import ohmattos_client
from app.utils.validators import Validators

logger = logging.getLogger(__name__)


class PatientNotificationService:
    """Create patient portal, email, and SMS notifications without provider coupling."""

    @staticmethod
    def configured_channels() -> list[str]:
        raw_channels = os.getenv("HISPRO_PATIENT_NOTIFICATION_CHANNELS", "PORTAL,SMS")
        channels: list[str] = []
        for value in raw_channels.split(","):
            channel = value.strip().upper()
            if not channel or channel in channels:
                continue
            if channel not in PatientNotification.CHANNELS:
                logger.warning("Ignoring unsupported patient notification channel: %s", channel)
                continue
            channels.append(channel)
        return channels or ["PORTAL"]

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
        channels = PatientNotificationService.configured_channels() if channels is None else channels
        for channel in channels:
            normalized_channel = channel.upper()
            if normalized_channel not in PatientNotification.CHANNELS:
                logger.warning("Ignoring unsupported patient notification channel: %s", normalized_channel)
                continue
            status = "QUEUED"
            if normalized_channel == "SMS" and not patient.phone:
                status = "SUPPRESSED"
            if normalized_channel == "EMAIL" and not patient.email:
                status = "SUPPRESSED"

            notification = PatientNotification(
                id=str(uuid.uuid4()),
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
            user_id=f"patient:{patient.id}",
            channel_type=channel.lower(),
            recipient=patient.phone if channel == "SMS" else patient.email,
            subject=Validators.sanitize_string(title),
            body=Validators.sanitize_string(message),
            idempotency_key=f"hispro:patient-notification:{notification.id}",
        )
        external_data = result.get("data") or {}
        external_status = external_data.get("status")
        metadata = dict(notification.metadata_json or {})
        metadata["ohmattos_delivery"] = {
            "accepted": bool(result.get("ok")),
            "queued": bool(result.get("ok") and external_status == "queued"),
            "status": external_status,
            "message_id": external_data.get("message_id") if result.get("ok") else None,
            "deduplicated": bool(external_data.get("deduplicated")),
            "error": result.get("error") if not result.get("ok") else None,
        }
        notification.metadata_json = metadata
        if result.get("ok") and external_status == "skipped":
            notification.status = "SUPPRESSED"

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
