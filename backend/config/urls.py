"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.accounts.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/", include("apps.accounts.urls")),
    path("api/cases/", include("cases.urls")),
    path("api/", include("apps.evidence.urls")),

    # Existing JWT endpoints preserved with dual username/email support
    path("api/token/", LoginView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]