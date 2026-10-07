from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Case
from .pagination import CasePagination
from .serializers import CaseSerializer


class CaseListCreateView(generics.ListCreateAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CasePagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at", "title", "priority", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Admin can view all cases if permitted; investigators strictly view their own
        if getattr(self.request.user, "role", None) == "ADMIN" or self.request.user.is_superuser:
            queryset = Case.objects.all().order_by("-created_at")
        else:
            queryset = Case.objects.filter(investigator=self.request.user).order_by("-created_at")

        status_param = self.request.query_params.get("status")
        if status_param:
            valid_statuses = [choice[0] for choice in Case.STATUS_CHOICES]
            status_val = status_param.strip().upper()
            if status_val not in valid_statuses:
                raise ValidationError(
                    {"status": f"Invalid status '{status_param}'. Valid choices are: {', '.join(valid_statuses)}."}
                )
            queryset = queryset.filter(status=status_val)

        priority_param = self.request.query_params.get("priority")
        if priority_param:
            valid_priorities = [choice[0] for choice in Case.PRIORITY_CHOICES]
            priority_val = priority_param.strip().upper()
            if priority_val not in valid_priorities:
                raise ValidationError(
                    {"priority": f"Invalid priority '{priority_param}'. Valid choices are: {', '.join(valid_priorities)}."}
                )
            queryset = queryset.filter(priority=priority_val)

        return queryset

    def perform_create(self, serializer):
        serializer.save(investigator=self.request.user)


class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self.request.user, "role", None) == "ADMIN" or self.request.user.is_superuser:
            return Case.objects.all()
        return Case.objects.filter(investigator=self.request.user)


class CaseCloseView(APIView):
    """
    POST /api/cases/<int:pk>/close/
    Performs backend-enforced state transition OPEN -> CLOSED.
    Preserves all forensic evidence, hashes, reports, and custody records intact.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        if getattr(request.user, "role", None) == "ADMIN" or request.user.is_superuser:
            case = get_object_or_404(Case, pk=pk)
        else:
            case = get_object_or_404(Case, pk=pk, investigator=request.user)

        case.status = "CLOSED"
        case.save(update_fields=["status", "updated_at"])
        serializer = CaseSerializer(case)
        return Response(serializer.data, status=status.HTTP_200_OK)