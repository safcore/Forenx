"""Role and object-level permissions for investigations APIs."""

from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.models import UserRole


def _role(user) -> str | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "role", None)


def user_can_access_case(user, case) -> bool:
    """Return True when the user may access the given case."""
    role = _role(user)
    if role is None:
        return False
    if role in {UserRole.ADMINISTRATOR, UserRole.LEAD_INVESTIGATOR}:
        return True
    if case.investigator_id == user.id or case.created_by_id == user.id:
        return True
    return case.members.filter(id=user.id).exists()


class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


class CanManageCases(BasePermission):
    """Create/update cases: admin, lead, investigator."""

    def has_permission(self, request, view) -> bool:
        if not IsAuthenticatedAndActive().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _role(request.user) in {
            UserRole.ADMINISTRATOR,
            UserRole.LEAD_INVESTIGATOR,
            UserRole.INVESTIGATOR,
        }


class CanMutateEvidence(BasePermission):
    """Upload/mutate evidence: not auditor."""

    WRITE_ROLES = {
        UserRole.ADMINISTRATOR,
        UserRole.LEAD_INVESTIGATOR,
        UserRole.INVESTIGATOR,
        UserRole.ANALYST,
    }

    def has_permission(self, request, view) -> bool:
        if not IsAuthenticatedAndActive().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _role(request.user) in self.WRITE_ROLES


class CanRunAnalysis(BasePermission):
    """Run analysis endpoints (including report/AI)."""

    WRITE_ROLES = {
        UserRole.ADMINISTRATOR,
        UserRole.LEAD_INVESTIGATOR,
        UserRole.INVESTIGATOR,
        UserRole.ANALYST,
    }

    def has_permission(self, request, view) -> bool:
        if not IsAuthenticatedAndActive().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _role(request.user) in self.WRITE_ROLES


class CanAccessCaseObject(BasePermission):
    """Object-level case access."""

    def has_object_permission(self, request, view, obj) -> bool:
        case = obj if obj.__class__.__name__ == "Case" else getattr(obj, "case", None)
        if case is None:
            return False
        if not user_can_access_case(request.user, case):
            return False
        role = _role(request.user)
        if request.method in SAFE_METHODS:
            return True
        # Auditors are read-only.
        if role == UserRole.AUDITOR:
            return False
        # Analysts cannot destroy/reassign cases.
        if role == UserRole.ANALYST and obj.__class__.__name__ == "Case":
            return request.method not in {"PUT", "PATCH", "DELETE"}
        return True
