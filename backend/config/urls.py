from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from mural.contas import CadastroViewSet, EuView, LoginView, RegistroView
from mural.views import (
    AmigoViewSet,
    ComentarioViewSet,
    FilmeViewSet,
    FotoComentarioViewSet,
    SessaoViewSet,
    TMDBBuscaView,
)

router = DefaultRouter()
router.register("filmes", FilmeViewSet, basename="filme")
router.register("amigos", AmigoViewSet, basename="amigo")
router.register("sessoes", SessaoViewSet, basename="sessao")
router.register("comentarios", ComentarioViewSet, basename="comentario")
router.register("fotos", FotoComentarioViewSet, basename="foto")
router.register("cadastros", CadastroViewSet, basename="cadastro")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/registro/", RegistroView.as_view(), name="registro"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api/auth/eu/", EuView.as_view(), name="eu"),
    path("api/tmdb/buscar/", TMDBBuscaView.as_view(), name="tmdb-buscar"),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Fotos enviadas: em desenvolvimento, pelo helper static(); em produção, pela view serve, que
# basta para o tamanho do grupo.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
