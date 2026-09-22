from django.urls import path
from .views import RegisterView, ProfileView, LoginView

urlpatterns = [
    # Existing endpoints preserved
    path("register/", RegisterView.as_view(), name="register"),
    path("profile/", ProfileView.as_view(), name="profile"),

    # Auth routes
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
]