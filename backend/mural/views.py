from django.conf import settings
from django.db.models import Case, Count, IntegerField, Value, When
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from . import tmdb
from .filters import SessaoFilter
from .models import TIER_RANK, Amigo, Comentario, Filme, FotoComentario, Sessao, Tier
from .permissions import DonoOuAdmin, LeituraPublicaEscritaAdmin
from .serializers import (
    AmigoSerializer,
    ComentarioSerializer,
    FilmeSerializer,
    FotoComentarioSerializer,
    SessaoSerializer,
    TMDBResultadoSerializer,
)


def _tiers_vazias():
    return {valor: [] for valor in Tier.values}


class AmigoViewSet(ModelViewSet):
    """Participantes do grupo e seus ícones. Leitura pública; só a admin altera."""

    queryset = Amigo.objects.all()
    serializer_class = AmigoSerializer
    permission_classes = [LeituraPublicaEscritaAdmin]
    search_fields = ("apelido",)
    ordering_fields = ("apelido",)


class FilmeViewSet(ModelViewSet):
    """Catálogo de títulos (filmes e séries). Leitura pública; só a admin altera
    diretamente (os amigos criam títulos ao cadastrar uma sessão com ``tmdb_id``)."""

    queryset = Filme.objects.all()
    serializer_class = FilmeSerializer
    permission_classes = [LeituraPublicaEscritaAdmin]
    filterset_fields = ("tipo", "genero", "ano_lancamento")
    search_fields = ("titulo", "diretor", "genero")
    ordering_fields = ("titulo", "ano_lancamento")

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Este título tem sessões registradas e não pode ser apagado."},
                status=400,
            )


class SessaoViewSet(ModelViewSet):
    """Recurso principal: cada sessão é um 'cartaz' do mural.

    Leitura pública. Amigos logados criam sessões e alteram as que criaram;
    a administradora altera qualquer uma."""

    serializer_class = SessaoSerializer
    filterset_class = SessaoFilter
    permission_classes = [DonoOuAdmin]
    search_fields = ("filme__titulo", "filme__diretor", "sugerido_por__apelido")
    # tier_rank ordena S > A > B > C > VTNC (ordem alfabética não serviria).
    ordering_fields = ("data_exibicao", "ano", "tier_rank", "filme__titulo")
    ordering = ("-ano", "-data_exibicao", "filme__titulo")

    def get_queryset(self):
        rank = Case(
            *[When(tier=t, then=Value(r)) for t, r in TIER_RANK.items()],
            default=Value(0),
            output_field=IntegerField(),
        )
        return (
            Sessao.objects.select_related("filme")
            .prefetch_related("sugerido_por")
            .annotate(tier_rank=rank)
            .all()
        )

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    @extend_schema(
        responses={200: dict},
        description=(
            "Tier lists agrupadas por ano (anos mais recentes primeiro), com o nome "
            "do ano do grupo (2024 = Ano 1). "
            "Cada ano traz as tiers S, A, B, C e VTNC com os filmes de cada uma. "
            "Aceita os mesmos filtros da listagem. Com ?ano=N o ano pedido sempre "
            "aparece, mesmo sem filmes (tiers vazias)."
        ),
    )
    @action(detail=False, methods=["get"], url_path="tier-lists", pagination_class=None)
    def tier_lists(self, request):
        sessoes = (
            self.filter_queryset(self.get_queryset())
            .filter(tier__isnull=False)
            .order_by("ano", "data_exibicao", "filme__titulo")
        )

        por_ano = {}
        for sessao in sessoes:
            tiers = por_ano.setdefault(sessao.ano, _tiers_vazias())
            dados = SessaoSerializer(sessao, context=self.get_serializer_context()).data
            tiers[sessao.tier].append(dados)

        ano_pedido = request.query_params.get("ano", "")
        if ano_pedido.isdigit():
            por_ano.setdefault(int(ano_pedido), _tiers_vazias())

        inicio = settings.ANO_INICIO_GRUPO
        resultado = [
            {
                "ano": ano,
                "ano_do_grupo": ano - inicio + 1,
                "nome": f"Ano {ano - inicio + 1}",
                "tiers": por_ano[ano],
            }
            for ano in sorted(por_ano, reverse=True)
        ]
        return Response(resultado)

    @extend_schema(
        responses={200: dict},
        description=(
            "Abas do mural: do ano em que o grupo começou até o ano atual (em ordem "
            "crescente), com o total de filmes avaliados em cada um. "
            "'ano_atual' é a aba que a página inicial deve abrir."
        ),
    )
    @action(detail=False, methods=["get"], pagination_class=None)
    def anos(self, request):
        atual = timezone.localdate().year
        totais = dict(
            Sessao.objects.filter(tier__isnull=False)
            .order_by()
            .values_list("ano")
            .annotate(total=Count("id"))
        )
        inicio = settings.ANO_INICIO_GRUPO
        anos = [
            {
                "ano": ano,
                "ano_do_grupo": ano - inicio + 1,
                "nome": f"Ano {ano - inicio + 1}",
                "total": totais.get(ano, 0),
            }
            for ano in range(inicio, atual + 1)
        ]
        return Response({"ano_atual": atual, "anos": anos})

    @extend_schema(
        responses=SessaoSerializer(many=True),
        description="Próximas sessões: de hoje em diante e ainda sem tier, da mais próxima à mais distante.",
    )
    @action(detail=False, methods=["get"], pagination_class=None)
    def proximas(self, request):
        sessoes = (
            self.get_queryset()
            .filter(data_exibicao__gte=timezone.localdate(), tier__isnull=True)
            .order_by("data_exibicao")
        )
        return Response(self.get_serializer(sessoes, many=True).data)


class ComentarioViewSet(ModelViewSet):
    """Comentários (com fotos). Só para usuários logados; cada um altera os seus."""

    queryset = (
        Comentario.objects.select_related("autor", "sessao")
        .prefetch_related("fotos")
        .all()
    )
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticated, DonoOuAdmin]
    filterset_fields = ("sessao", "autor")
    search_fields = ("texto", "autor__apelido")
    ordering_fields = ("criado_em",)

    def perform_create(self, serializer):
        amigo = getattr(self.request.user, "amigo", None)
        if amigo is None:
            raise PermissionDenied("Sua conta ainda não está ligada a um amigo do grupo.")
        serializer.save(autor=amigo)


class FotoComentarioViewSet(mixins.DestroyModelMixin, GenericViewSet):
    """Apagar uma foto de comentário (o dono do comentário ou a administradora)."""

    queryset = FotoComentario.objects.select_related("comentario__autor")
    serializer_class = FotoComentarioSerializer
    permission_classes = [IsAuthenticated, DonoOuAdmin]


class TMDBBuscaView(APIView):
    """Busca filmes e séries no TMDB para o amigo escolher ao cadastrar uma sessão."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tmdb"

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, required=True, description="Parte do título."),
            OpenApiParameter("ano", int, description="Ano de lançamento ou de estreia (desempata remakes)."),
        ],
        responses=TMDBResultadoSerializer(many=True),
    )
    def get(self, request):
        texto = request.query_params.get("q", "").strip()
        if len(texto) < 2:
            return Response({"q": "Digite pelo menos 2 letras."}, status=400)
        ano = request.query_params.get("ano", "")
        try:
            resultados = tmdb.buscar(texto, int(ano) if ano.isdigit() else None)
        except tmdb.TMDBError as erro:
            return Response({"detail": str(erro)}, status=502)
        return Response(resultados)
