import logging
import os
import uuid
from datetime import datetime

from app.extensions import db_session
from app.models.patient import Patient
from app.models.patient_notification import PatientNotification
from app.services.integration_outbox_service import IntegrationOutboxService
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
                facility_id=patient.facility_id,
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
            PatientNotificationService._queue_ohmattos_delivery(notification, patient)
        db_session.flush()
        return created

    @staticmethod
    def _queue_ohmattos_delivery(
        notification: PatientNotification,
        patient: Patient,
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
        if not patient.facility_id:
            logger.warning("Skipping OhmattOS notification without an immutable facility ID")
            return

        idempotency_key = f"hispro:patient-notification:{notification.id}"
        IntegrationOutboxService.enqueue(
            facility_id=str(patient.facility_id),
            event_type="notification.send",
            aggregate_type="patient_notification",
            aggregate_id=str(notification.id),
            idempotency_key=idempotency_key,
            payload={
                "user_id": f"patient:{patient.id}",
                "channel_type": channel.lower(),
                "recipient": patient.phone if channel == "SMS" else patient.email,
                "subject": notification.title,
                "body": notification.message,
                "template_id": None,
                "idempotency_key": idempotency_key,
            },
            session=db_session,
        )
        metadata = dict(notification.metadata_json or {})
        metadata["ohmattos_delivery"] = {
            "queued_locally": True,
            "status": "pending_dispatch",
            "idempotency_key": idempotency_key,
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
