"""Account serializers for registration and profile."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import UserRole

User = get_user_model()


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login accepting frontend ``email`` or classic ``username``.

    Frontend contract sends ``{email, password}``. Django's user model still
    authenticates via ``USERNAME_FIELD`` (username); email is resolved first.
    Username+password continues to work for existing API clients/tests.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep password; accept either identifier without requiring username.
        self.fields[self.username_field] = serializers.CharField(required=False, allow_blank=True)
        self.fields["email"] = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip()
        username = (attrs.get(self.username_field) or "").strip()

        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"detail": "No active account found with the given credentials"},
                    code="authorization",
                ) from exc
            except User.MultipleObjectsReturned as exc:
                raise serializers.ValidationError(
                    {"email": "Multiple accounts share this email; sign in with username."},
                    code="authorization",
                ) from exc
            attrs[self.username_field] = user.get_username()
        elif not username:
            raise serializers.ValidationError(
                {"detail": "Provide email or username with password."},
                code="authorization",
            )

        return super().validate(attrs)


class RegisterSerializer(serializers.ModelSerializer):
    """Create a user account (defaults to investigator unless elevated)."""

    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.INVESTIGATOR,
        required=False,
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name", "role")
        read_only_fields = ("id",)

    def validate_role(self, value: str) -> str:
        request = self.context.get("request")
        # Only administrators may create elevated roles via API.
        if value in {
            UserRole.ADMINISTRATOR,
            UserRole.LEAD_INVESTIGATOR,
            UserRole.AUDITOR,
        }:
            if request is None or not request.user.is_authenticated:
                return UserRole.INVESTIGATOR
            if getattr(request.user, "role", None) != UserRole.ADMINISTRATOR:
                return UserRole.INVESTIGATOR
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Public user profile fields."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields
