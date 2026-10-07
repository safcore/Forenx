from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from .utils import (
    create_verification_token,
    is_disposable_email,
    send_verification_email,
)

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
        ]
        read_only_fields = ("role",)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if not normalized_email:
            raise serializers.ValidationError("This field may not be blank.")
        if is_disposable_email(normalized_email):
            raise serializers.ValidationError("Disposable email addresses are not permitted.")
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate(self, attrs):
        user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone"),
            role="INVESTIGATOR",
            is_email_verified=False,
        )
        token_obj = create_verification_token(user)
        send_verification_email(user, token_obj)
        return user


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allows authenticating with either username+password or email+password and enforces verification & active status."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False
        self.fields["email"] = serializers.CharField(required=False, write_only=True)

    def validate(self, attrs):
        username_or_email = attrs.get(self.username_field) or attrs.get("email")
        password = attrs.get("password")

        if not username_or_email or not password:
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        # Lookup by username first; fall back to case-insensitive email
        user = User.objects.filter(username=username_or_email).first()
        if not user:
            user = User.objects.filter(email__iexact=username_or_email).first()

        if user is None or not user.check_password(password):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                "Account is deactivated. Please contact an administrator.",
                "account_deactivated",
            )

        if not getattr(user, "is_email_verified", True):
            raise exceptions.AuthenticationFailed(
                "Email address is not verified. Please verify your email before signing in.",
                "email_not_verified",
            )

        if not api_settings.USER_AUTHENTICATION_RULE(user):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        self.user = user
        refresh = self.get_token(self.user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "is_email_verified",
            "created_at",
            "date_joined",
            "last_login",
        ]


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "is_email_verified",
            "created_at",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "username", "email", "created_at", "date_joined", "last_login"]


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=["ADMIN", "INVESTIGATOR"], required=False)
    is_active = serializers.BooleanField(required=False)
    is_email_verified = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["role", "is_active", "is_email_verified"]

    def validate(self, attrs):
        request = self.context.get("request")
        target_user = self.instance

        if not request or not request.user:
            return attrs

        # 1. Users cannot change their own role
        if "role" in attrs and target_user.id == request.user.id:
            if attrs["role"] != target_user.role:
                raise serializers.ValidationError({"role": "You cannot modify your own role."})

        # 2. Cannot demote the last active administrator
        if attrs.get("role") and attrs["role"] != "ADMIN" and target_user.role == "ADMIN":
            active_admin_count = User.objects.filter(role="ADMIN", is_active=True).count()
            if active_admin_count <= 1:
                raise serializers.ValidationError({"role": "Cannot demote the last active administrator."})

        # 3. Cannot deactivate the last active administrator
        if attrs.get("is_active") is False and target_user.role == "ADMIN":
            active_admin_count = User.objects.filter(role="ADMIN", is_active=True).count()
            if active_admin_count <= 1:
                raise serializers.ValidationError({"is_active": "Cannot deactivate the last active administrator."})

        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, trim_whitespace=True)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)