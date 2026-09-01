from django.urls import path
from .views import CaseListCreateView, CaseDetailView

urlpatterns = [
    path("", CaseListCreateView.as_view(), name="case-list-create"),
    path("<int:pk>/", CaseDetailView.as_view(), name="case-detail"),
]