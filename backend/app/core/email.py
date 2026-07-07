from typing import Optional
import boto3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException, status
from app.core.config import settings


class EmailService:
    def __init__(self):
        self._ses_client = None

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> None:
        """
        Send email using the configured email provider.

        Args:
            recipient_email: Recipient email address
            subject: Email subject
            body_text: Plain text email body
            body_html: HTML email body (optional)
        """
        if settings.EMAIL_PROVIDER == "aws_ses":
            self._send_via_aws_ses(recipient_email, subject, body_text, body_html)
        elif settings.EMAIL_PROVIDER == "smtp":
            self._send_via_smtp(recipient_email, subject, body_text, body_html)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid email provider: {settings.EMAIL_PROVIDER}. Must be 'aws_ses' or 'smtp'",
            )

    def _send_via_aws_ses(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> None:
        """Send email via AWS SES"""
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AWS SES credentials are not configured.",
            )

        if not settings.SENDER_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SENDER_EMAIL is not configured.",
            )

        ses_client = self._get_ses_client()

        message_body = {"Text": {"Data": body_text}}
        if body_html:
            message_body["Html"] = {"Data": body_html}

        try:
            ses_client.send_email(
                Source=settings.SENDER_EMAIL,
                Destination={"ToAddresses": [recipient_email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": message_body,
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email via AWS SES: {str(e)}",
            ) from e

    def _send_via_smtp(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> None:
        """Send email via SMTP"""
        if not settings.SMTP_HOST:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SMTP_HOST is not configured.",
            )

        if not settings.SENDER_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SENDER_EMAIL is not configured.",
            )

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SENDER_EMAIL
        msg["To"] = recipient_email

        # Add text and HTML parts
        part1 = MIMEText(body_text, "plain")
        msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

        # Connect to SMTP server and send
        try:
            if settings.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

            if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email via SMTP: {str(e)}",
            ) from e

    def _get_ses_client(self):
        """Get or create AWS SES client"""
        if self._ses_client is not None:
            return self._ses_client

        try:
            self._ses_client = boto3.client(
                "ses",
                region_name=settings.AWS_SES_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to initialize AWS SES client.",
            ) from exc

        return self._ses_client
