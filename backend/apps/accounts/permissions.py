from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Allows access only to authenticated users with the ADMIN role or superuser status.
    Strictly enforced at the backend API layer.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, "role", None) == "ADMIN" or request.user.is_superuser)
        )


class IsInvestigatorOrAdmin(BasePermission):
    """
    Allows access to authenticated users who are either Investigators or Admins.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "role", None) in ["ADMIN", "INVESTIGATOR", "LEAD", "ANALYST"]
                or request.user.is_superuser
            )
        )
