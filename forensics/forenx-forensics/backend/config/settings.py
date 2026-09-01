"""Django settings for the ForenX API integration backend.

This package is a host/adapter around the standalone forensic engine in ``app/``.
It must never be imported by core forensic modules.
"""

from __future__ import annotations

import os
import urllib.parse
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# backend/config/settings.py -> backend/ -> repo root
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _env_bool(*names: str, default: bool = False) -> bool:
    raw = _env_first(*names, default="")
    if raw == "":
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = _env_bool("DEBUG", "DJANGO_DEBUG", default=True)

SECRET_KEY = _env_first("SECRET_KEY", "DJANGO_SECRET_KEY")
_INSECURE_DEV_KEY = "dev-only-insecure-forenx-change-me-before-production"
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _INSECURE_DEV_KEY
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is False.")
if not DEBUG and (
    SECRET_KEY == _INSECURE_DEV_KEY or len(SECRET_KEY) < 50
):
    raise ImproperlyConfigured(
        "SECRET_KEY must be a unique, 50+ character value when DEBUG is False."
    )

_allowed = _env_first(
    "ALLOWED_HOSTS",
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1,testserver" if DEBUG else "",
)
ALLOWED_HOSTS = _csv(_allowed)
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set when DEBUG is False.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "accounts",
    "investigations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CorsMiddleware must be before CommonMiddleware so preflight OPTIONS are handled.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Explicit allow-list only — never CORS_ALLOW_ALL_ORIGINS.
_cors_default = "http://localhost:5173,http://127.0.0.1:5173" if DEBUG else ""
CORS_ALLOWED_ORIGINS = _csv(
    _env_first("CORS_ALLOWED_ORIGINS", default=_cors_default)
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

_csrf_trusted = _env_first("CSRF_TRUSTED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = _csv(_csrf_trusted) if _csrf_trusted else list(CORS_ALLOWED_ORIGINS)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default for local/dev/tests; PostgreSQL via DATABASE_URL.
DATABASE_URL = _env_first("DATABASE_URL")


def _database_from_url(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "").split("+", 1)[0].lower()
    if scheme in {"postgres", "postgresql"}:
        query = urllib.parse.parse_qs(parsed.query)
        options: dict[str, str] = {}
        if "sslmode" in query:
            options["sslmode"] = query["sslmode"][0]
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": urllib.parse.unquote(parsed.path.lstrip("/")),
            "USER": urllib.parse.unquote(parsed.username or ""),
            "PASSWORD": urllib.parse.unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
            "OPTIONS": options,
            "CONN_MAX_AGE": int(_env_first("DB_CONN_MAX_AGE", default="60")),
        }
    if scheme in {"sqlite", "sqlite3"}:
        name = urllib.parse.unquote(parsed.path) or str(BASE_DIR / "db.sqlite3")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }
    raise ImproperlyConfigured(
        "DATABASE_URL must use postgresql:// or sqlite:// schemes."
    )


if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

# Forensic evidence and derived artifacts live outside source packages.
STORAGE_ROOT = Path(
    _env_first("FORENX_STORAGE_ROOT", default=str(REPO_ROOT / "storage"))
).resolve()
EVIDENCE_STORAGE_DIR = STORAGE_ROOT / "evidence"
REPORT_STORAGE_DIR = STORAGE_ROOT / "reports"
MEDIA_ROOT = STORAGE_ROOT
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "EXCEPTION_HANDLER": "investigations.api_errors.forenx_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Upload / analysis guards
FORENX_MAX_UPLOAD_BYTES = int(
    _env_first("FORENX_MAX_UPLOAD_BYTES", default=str(50 * 1024 * 1024))
)
DATA_UPLOAD_MAX_MEMORY_SIZE = FORENX_MAX_UPLOAD_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = min(5 * 1024 * 1024, FORENX_MAX_UPLOAD_BYTES)
FORENX_BLOCKED_EXTENSIONS = frozenset(
    {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".msi",
        ".scr",
        ".ps1",
        ".vbs",
        ".js",
        ".jar",
        ".dll",
        ".sh",
    }
)

# Production TLS/HSTS. Terminate TLS at the reverse proxy and set
# SECURE_SSL_REDIRECT / cookie flags when DEBUG is False.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = int(_env_first("SECURE_HSTS_SECONDS", default="31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO" if not DEBUG else "DEBUG"},
}
