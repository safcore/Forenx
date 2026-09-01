"""Custom user model with forensic investigation roles."""

from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    """Backend authorization roles (Member 1)."""

    ADMINISTRATOR = "administrator", "Administrator"
    LEAD_INVESTIGATOR = "lead_investigator", "Lead Investigator"
    INVESTIGATOR = "investigator", "Investigator"
    ANALYST = "analyst", "Analyst"
    AUDITOR = "auditor", "Auditor"


class User(AbstractUser):
    """Application user with an investigation role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.INVESTIGATOR,
    )

    class Meta:
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
