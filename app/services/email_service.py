"""
Email Service - Framework Agnostic
Converted from Flask-Mail to standard smtplib for FastAPI compatibility
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Email configuration from environment
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@hispro.com')


class EmailService:
    """Email notification service using standard SMTP"""

    @staticmethod
    def init_app(app):
        """
        Initialize email service (kept for compatibility).
        In FastAPI, nothing needed as config is read from environment.
        """
        pass

    @staticmethod
    def _send_smtp(to: str, subject: str, body: str, html: Optional[str] = None) -> tuple:
        """Send email via SMTP"""
        if not all([MAIL_USERNAME, MAIL_PASSWORD]):
            return False, "Email configuration incomplete"

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = MAIL_DEFAULT_SENDER or MAIL_USERNAME
            msg['To'] = to

            # Attach plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Attach HTML part if provided
            if html:
                html_part = MIMEText(html, 'html')
                msg.attach(html_part)

            # Connect to SMTP server
            with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
                server.ehlo()
                if MAIL_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
                server.send_message(msg)

            return True, "Email sent successfully"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> tuple:
        """Send email"""
        return EmailService._send_smtp(to, subject, body, html)

    @staticmethod
    def send_password_reset_email(email: str, reset_token: str):
        """Send password reset email"""
        reset_link = f"http://localhost:5173/reset-password?token={reset_token}"

        subject = "Password Reset Request - HIS.Pro"
        body = f"""Hello,

You have requested to reset your password for HIS.Pro.

Please click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
HIS.Pro Team
        """

        html = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2b8cee;">Password Reset Request</h2>
        <p>Hello,</p>
        <p>You have requested to reset your password for HIS.Pro.</p>
        <p>Please click the button below to reset your password:</p>
        <p style="text-align: center;">
            <a href="{reset_link}" style="background-color: #2b8cee; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Reset Password</a>
        </p>
        <p style="color: #666; font-size: 14px;">This link will expire in 1 hour.</p>
        <p style="color: #666; font-size: 14px;">If you did not request this password reset, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>HIS.Pro Team</p>
    </div>
</body>
</html>
        """

        return EmailService.send_email(email, subject, body, html)

    @staticmethod
    def send_welcome_email(email: str, first_name: str):
        """Send welcome email to new user"""
        subject = "Welcome to HIS.Pro"
        body = f"""Hello {first_name},

Welcome to HIS.Pro! Your account has been created successfully.

You can now log in to access the hospital information system.

Best regards,
HIS.Pro Team
        """

        html = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2b8cee;">Welcome to HIS.Pro!</h2>
        <p>Hello {first_name},</p>
        <p>Your account has been created successfully.</p>
        <p>You can now log in to access the hospital information system.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>HIS.Pro Team</p>
    </div>
</body>
</html>
        """

        return EmailService.send_email(email, subject, body, html)

    @staticmethod
    def send_appointment_reminder(email: str, patient_name: str, appointment_date: str, doctor_name: str):
        """Send appointment reminder email"""
        subject = "Appointment Reminder - HIS.Pro"
        body = f"""Hello {patient_name},

This is a reminder for your upcoming appointment:

Date: {appointment_date}
Doctor: {doctor_name}

Please arrive 15 minutes before your scheduled time.

Best regards,
HIS.Pro Team
        """

        html = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2b8cee;">Appointment Reminder</h2>
        <p>Hello {patient_name},</p>
        <p>This is a reminder for your upcoming appointment:</p>
        <div style="background-color: #f5f5f7; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p style="margin: 5px 0;"><strong>Date:</strong> {appointment_date}</p>
            <p style="margin: 5px 0;"><strong>Doctor:</strong> {doctor_name}</p>
        </div>
        <p>Please arrive 15 minutes before your scheduled time.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">Best regards,<br>HIS.Pro Team</p>
    </div>
</body>
</html>
        """

        return EmailService.send_email(email, subject, body, html)
