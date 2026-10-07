from django.urls import path
from .views import (
    AdminUserDetailView,
    AdminUserListView,
    LoginView,
    ProfileView,
    RegisterView,
    ResendVerificationView,
    VerifyEmailView,
)

urlpatterns = [
    # Existing endpoints preserved
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),

    # Auth routes
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),

    # Email verification routes
    path("auth/verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("auth/resend-verification/", ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),

    # Admin User Management routes (strictly protected by IsAdminRole)
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]