from django.urls import path
from .views import CaseCloseView, CaseDetailView, CaseListCreateView

urlpatterns = [
    path("", CaseListCreateView.as_view(), name="case-list-create"),
    path("<int:pk>/", CaseDetailView.as_view(), name="case-detail"),
    path("<int:pk>/close/", CaseCloseView.as_view(), name="case-close"),
]