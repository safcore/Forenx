import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone as dj_timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('INVESTIGATOR', 'Investigator'),
        ('LEAD', 'Lead Investigator'),
        ('ANALYST', 'Analyst'),
        ('AUDITOR', 'Auditor'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='INVESTIGATOR'
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    is_email_verified = models.BooleanField(
        default=True,
        help_text="Designates whether the user's email has been verified."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_tokens"
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self) -> bool:
        return not self.is_used and dj_timezone.now() < self.expires_at

    def __str__(self):
        return f"Token for {self.user.username} (used={self.is_used})"