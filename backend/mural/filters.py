from django_filters import rest_framework as filters

from .models import Sessao, Tier


class SessaoFilter(filters.FilterSet):
    # Filtra pelo campo "ano" (que também existe nas sessões sem data exata).
    ano = filters.NumberFilter(field_name="ano")
    tier = filters.ChoiceFilter(choices=Tier.choices)
    sugerido_por = filters.CharFilter(
        field_name="sugerido_por__apelido", lookup_expr="iexact", distinct=True
    )
    titulo = filters.CharFilter(field_name="filme__titulo", lookup_expr="icontains")
    filme = filters.NumberFilter(
        field_name="filme__id",
        help_text="Todas as exibições de um filme (útil para 'também exibido em').",
    )
    data_inicial = filters.DateFilter(field_name="data_exibicao", lookup_expr="gte")
    data_final = filters.DateFilter(field_name="data_exibicao", lookup_expr="lte")
    avaliada = filters.BooleanFilter(
        method="filtrar_avaliada",
        help_text="true = só sessões com tier; false = só as ainda sem tier.",
    )

    class Meta:
        model = Sessao
        fields = (
            "ano",
            "tier",
            "sugerido_por",
            "titulo",
            "filme",
            "data_inicial",
            "data_final",
            "avaliada",
        )

    def filtrar_avaliada(self, queryset, name, value):
        return queryset.filter(tier__isnull=not value)
