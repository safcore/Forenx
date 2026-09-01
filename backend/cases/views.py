from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Case
from .serializers import CaseSerializer


class CaseListCreateView(generics.ListCreateAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Case.objects.filter(investigator=self.request.user)

    def perform_create(self, serializer):
        serializer.save(investigator=self.request.user)


class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Case.objects.filter(investigator=self.request.user)