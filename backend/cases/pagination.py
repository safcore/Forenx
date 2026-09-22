from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class CasePagination(PageNumberPagination):
    """Configurable pagination for case listings."""

    page_size = getattr(settings, "CASE_PAGE_SIZE", 10)
    page_size_query_param = "page_size"
    max_page_size = 100
