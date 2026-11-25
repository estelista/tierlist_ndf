from rest_framework.pagination import PageNumberPagination


class PaginacaoPadrao(PageNumberPagination):
    """Paginação por número de página. O cliente pode escolher ?page_size= (máx. 100)."""

    page_size_query_param = "page_size"
    max_page_size = 100
