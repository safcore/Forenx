from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated

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
        # Strict ownership isolation: users only access their own cases
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
        return Case.objects.filter(investigator=self.request.user)