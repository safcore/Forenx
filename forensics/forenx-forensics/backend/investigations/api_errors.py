"""Consistent API error envelope for ForenX Django endpoints."""

from __future__ import annotations

import logging
import re
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from app.utils.exceptions import ForenXError

logger = logging.getLogger(__name__)

_SENSITIVE_TEXT = re.compile(
    r"(traceback|file://|[A-Za-z]:\\|/home/|/Users/|/var/|/tmp/|/opt/|"
    r"stored_path|SECRET_KEY|api[_-]?key|\.py:\d+)",
    re.IGNORECASE,
)


def sanitize_client_error_message(message: str, *, fallback: str) -> str:
    """Return an investigator-safe error string with paths/secrets removed."""
    text = str(message or "").strip()
    if not text or _SENSITIVE_TEXT.search(text):
        return fallback
    return text[:300]


class ApiError(Exception):
    """Structured application API error."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def success_payload(data: Any = None, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"success": True}
    if data is not None:
        body["data"] = data
    body.update(extra)
    return body


def forenx_exception_handler(exc, context):
    """Map domain/API errors to a consistent JSON envelope."""
    if isinstance(exc, ApiError):
        logger.warning("API error code=%s message=%s", exc.code, exc.message)
        return Response(
            error_payload(
                exc.code,
                sanitize_client_error_message(
                    exc.message, fallback="The request could not be completed."
                ),
                exc.details
                if exc.details is not None
                and not _SENSITIVE_TEXT.search(str(exc.details))
                else None,
            ),
            status=exc.http_status,
        )

    if isinstance(exc, ForenXError):
        logger.exception("ForenX engine error")
        return Response(
            error_payload(
                "FORENX_ENGINE_ERROR",
                sanitize_client_error_message(
                    str(exc),
                    fallback="The forensic operation could not be completed.",
                ),
            ),
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        message = "Request failed"
        if isinstance(detail, dict):
            if "detail" in detail:
                message = str(detail["detail"])
            else:
                message = "Validation failed"
        elif isinstance(detail, list) and detail:
            message = str(detail[0])
        code = "VALIDATION_ERROR" if response.status_code == 400 else "REQUEST_ERROR"
        if response.status_code == 401:
            code = "AUTHENTICATION_REQUIRED"
        elif response.status_code == 403:
            code = "PERMISSION_DENIED"
        elif response.status_code == 404:
            code = "NOT_FOUND"
        message = sanitize_client_error_message(
            message, fallback="An unexpected error occurred."
        )
        response.data = error_payload(code, message, None)
        return response

    logger.exception("Unhandled API exception")
    return Response(
        error_payload("INTERNAL_ERROR", "An unexpected error occurred."),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
