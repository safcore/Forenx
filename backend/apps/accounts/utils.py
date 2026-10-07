import logging
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone as dj_timezone

from .models import EmailVerificationToken, User

logger = logging.getLogger(__name__)

DISPOSABLE_DOMAINS = frozenset({
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    "sharklasers.com",
    "trashmail.com",
    "yopmail.com",
    "dispostable.com",
    "getairmail.com",
    "throwawaymail.com",
})


def is_disposable_email(email: str) -> bool:
    """Check if the email belongs to a known disposable email domain."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[-1].strip().lower()
    return domain in DISPOSABLE_DOMAINS


def create_verification_token(user: User) -> EmailVerificationToken:
    """Generate and persist a single-use, time-limited verification token for a user."""
    # Invalidate any prior active tokens for this user
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)

    token_str = secrets.token_urlsafe(32)
    expires_at = dj_timezone.now() + timedelta(hours=24)
    return EmailVerificationToken.objects.create(
        user=user,
        token=token_str,
        expires_at=expires_at,
        is_used=False,
    )


def send_verification_email(user: User, token_obj: EmailVerificationToken) -> bool:
    """Send verification email containing a secure link and token."""
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    verification_url = f"{frontend_url}/verify-email?token={token_obj.token}"
    subject = "Verify your ForenX account"
    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Thank you for registering on ForenX. Please verify your email address to activate your account:\n\n"
        f"{verification_url}\n\n"
        f"Verification Token: {token_obj.token}\n\n"
        f"This verification link will expire in 24 hours.\n\n"
        f"If you did not request this registration, please disregard this message.\n\n"
        f"— ForenX Digital Forensics Platform"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@forenx.local")

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to send verification email to %s: %s", user.email, exc)
        return False
