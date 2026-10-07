from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import EmailVerificationToken
from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    EmailOrUsernameTokenObtainPairSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    VerifyEmailSerializer,
)
from .utils import create_verification_token, send_verification_email

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class ProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_str = serializer.validated_data["token"].strip()

        token_obj = (
            EmailVerificationToken.objects.filter(token=token_str)
            .select_related("user")
            .first()
        )

        if not token_obj or not token_obj.is_valid():
            return Response(
                {"error": "Invalid or expired verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        token_obj.is_used = True
        token_obj.save(update_fields=["is_used"])

        return Response(
            {
                "message": "Email address verified successfully. You may now log in.",
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Avoid account enumeration while acknowledging receipt
            return Response(
                {
                    "message": "If an unverified account with this email exists, a verification link has been sent."
                },
                status=status.HTTP_200_OK,
            )

        if user.is_email_verified:
            return Response(
                {"error": "This email address is already verified. Please sign in."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_obj = create_verification_token(user)
        send_verification_email(user, token_obj)

        return Response(
            {"message": "A verification email has been sent to your address."},
            status=status.HTTP_200_OK,
        )


class AdminUserListView(generics.ListAPIView):
    """
    List all users in the system. Admin-only.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update user status and roles. Admin-only.
    """

    queryset = User.objects.all()
    permission_classes = [IsAdminRole]

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return AdminUserUpdateSerializer
        return AdminUserSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return full representation after update
        read_serializer = AdminUserSerializer(instance)
        return Response(read_serializer.data, status=status.HTTP_200_OK)