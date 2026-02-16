"""Email sending utilities for authentication."""

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from api.config import Settings


def get_mail_config() -> ConnectionConfig:
    """Create mail configuration from settings.

    Returns:
        FastMail connection configuration
    """
    settings = Settings()
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=bool(settings.MAIL_USERNAME),
        VALIDATE_CERTS=True,
    )


async def send_reset_email(email: str, token: str) -> None:
    """Send password reset email with token link.

    In development (no email configured), prints to console instead.

    Args:
        email: Recipient email address
        token: Password reset token
    """
    settings = Settings()
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    # If email not configured, log to console (dev mode)
    if not settings.MAIL_USERNAME:
        print(f"[DEV] Password reset link for {email}: {reset_url}")
        return

    message = MessageSchema(
        subject="CFU-Counter Password Reset",
        recipients=[email],
        body=f"""You requested a password reset for your CFU-Counter account.

Click the link below to reset your password (expires in 15 minutes):

{reset_url}

If you didn't request this, you can safely ignore this email.

- The CFU-Counter Team
""",
        subtype="plain",
    )

    mail_config = get_mail_config()
    fm = FastMail(mail_config)
    await fm.send_message(message)
