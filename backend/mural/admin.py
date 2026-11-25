from django.contrib import admin

from .models import Amigo, Comentario, Filme, FotoComentario, Sessao


@admin.register(Amigo)
class AmigoAdmin(admin.ModelAdmin):
    list_display = ("apelido", "icone_url", "user")
    search_fields = ("apelido",)


@admin.register(Filme)
class FilmeAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "ano_lancamento", "diretor", "genero", "tmdb_id")
    search_fields = ("titulo", "diretor")
    list_filter = ("tipo", "genero")


@admin.register(Sessao)
class SessaoAdmin(admin.ModelAdmin):
    list_display = ("quando", "filme", "indicado_por", "tier", "criado_por")
    list_filter = ("tier", "ano", "sugerido_por")
    search_fields = ("filme__titulo",)
    filter_horizontal = ("sugerido_por",)

    @admin.display(description="Quando", ordering="ano")
    def quando(self, obj):
        return obj.data_exibicao or obj.ano

    @admin.display(description="Indicado por")
    def indicado_por(self, obj):
        return ", ".join(a.apelido for a in obj.sugerido_por.all())


class FotoComentarioInline(admin.TabularInline):
    model = FotoComentario
    extra = 0


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ("sessao", "autor", "criado_em")
    list_filter = ("autor",)
    inlines = [FotoComentarioInline]
