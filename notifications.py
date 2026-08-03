"""Email notification helpers for TutorLink.

This module intentionally keeps the implementation lightweight and safe:
it tries to send using environment-configured SMTP settings when available,
and otherwise returns a structured "skipped" result instead of failing the
primary request flow.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@tutorlink.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}


def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    *,
    from_email: Optional[str] = None,
) -> dict:
    """Send an email if SMTP settings are configured.

    Returns a structured payload so the app can remain resilient in local/dev
    environments where no SMTP relay is available.
    """

    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.info(
            "Email notification skipped for %s (%s) because SMTP settings are not configured.",
            to_email,
            subject,
        )
        return {
            "status": "skipped",
            "message": "SMTP settings are not configured",
            "recipient": to_email,
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email or SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - external SMTP failure branch
        logger.warning("Email notification failed for %s: %s", to_email, exc)
        return {
            "status": "failed",
            "message": str(exc),
            "recipient": to_email,
        }

    return {
        "status": "sent",
        "message": "Email notification delivered",
        "recipient": to_email,
    }


def send_booking_notification(
    to_email: str,
    booking_id: int,
    event_type: str,
    *,
    tutor_name: Optional[str] = None,
    student_name: Optional[str] = None,
) -> dict:
    """Convenience wrapper for a booking-related email notification."""

    if event_type == "created":
        subject = f"TutorLink booking request #{booking_id} created"
        body = (
            f"Your booking request for tutor {tutor_name or 'your selected tutor'} "
            f"has been created successfully."
        )
    elif event_type == "accepted":
        subject = f"TutorLink booking request #{booking_id} accepted"
        body = (
            f"Your booking request has been accepted by {tutor_name or 'the tutor'}. "
            f"Please review the session details."
        )
    elif event_type == "declined":
        subject = f"TutorLink booking request #{booking_id} declined"
        body = (
            f"Your booking request has been declined by {tutor_name or 'the tutor'}. "
            f"Please contact support if you need assistance."
        )
    else:
        subject = f"TutorLink booking request #{booking_id} updated"
        body = f"The booking request #{booking_id} has been updated."

    if student_name:
        body = f"Hello {student_name},\n\n{body}"

    return send_email_notification(to_email, subject, body)
