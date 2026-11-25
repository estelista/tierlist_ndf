from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from . import tmdb
from .models import Amigo, Comentario, Filme, FotoComentario, Sessao, Tipo


def _pode_editar(contexto, obj):
    """True se o usuário da requisição é o dono do objeto ou a administradora."""
    usuario = getattr(contexto.get("request"), "user", None)
    if usuario is None or not usuario.is_authenticated:
        return False
    return usuario.is_staff or (obj.dono_id is not None and obj.dono_id == usuario.id)


class AmigoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Amigo
        fields = ("id", "apelido", "icone_url")

    def validate_apelido(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "O apelido deve ter pelo menos 2 caracteres."
            )
        return value


class FilmeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filme
        fields = (
            "id",
            "tipo",
            "tmdb_id",
            "titulo",
            "ano_lancamento",
            "diretor",
            "genero",
            "sinopse",
            "poster_url",
        )

    def validate_titulo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("O título não pode ficar em branco.")
        return value

    def validate_ano_lancamento(self, value):
        # 1888 é o ano do primeiro filme conhecido.
        limite = timezone.localdate().year + 1
        if value < 1888 or value > limite:
            raise serializers.ValidationError(
                f"O ano de lançamento deve estar entre 1888 e {limite}."
            )
        return value


class TMDBResultadoSerializer(serializers.Serializer):
    """Só descreve a resposta da busca no TMDB (para a documentação)."""

    tipo = serializers.ChoiceField(choices=Tipo.choices)
    tmdb_id = serializers.IntegerField()
    titulo = serializers.CharField()
    titulo_original = serializers.CharField()
    ano_lancamento = serializers.IntegerField(allow_null=True)
    sinopse = serializers.CharField()
    poster_url = serializers.CharField()


def erros_da_sessao(data, ano, tier, admin):
    """Regras de data, ano e tier de uma sessão: devolve {campo: mensagem} (vazio se está tudo certo).

    Usada pela API e pelo importador do histórico. Quando há data, o ano é sempre o dela.
    """
    hoje = timezone.localdate()
    erros = {}

    if data is not None:
        ano = data.year
    elif not admin:
        # REGRA: só a administradora cadastra sessão sem data exata (histórico),
        # e só de anos anteriores ao atual.
        erros["data_exibicao"] = "Informe a data da sessão."
    elif ano is None:
        erros["ano"] = "Informe a data ou o ano da sessão."
    elif ano >= hoje.year:
        erros["ano"] = "Só anos anteriores ao atual podem ficar sem data exata."

    if ano is not None and ano < settings.ANO_INICIO_GRUPO:
        campo = "data_exibicao" if data is not None else "ano"
        erros[campo] = f"O grupo começou em {settings.ANO_INICIO_GRUPO}."

    # REGRA: sessão que já aconteceu tem tier; sessão futura (agendada) não pode ter.
    futura = data is not None and data > hoje
    if tier and futura:
        erros["tier"] = "Só é possível atribuir tier a uma sessão que já aconteceu."
    elif not tier and not futura:
        erros["tier"] = "Toda sessão que já aconteceu precisa ter tier."
    return erros


class SessaoSerializer(serializers.ModelSerializer):
    # Campos só de leitura, para o frontend montar o mural sem chamadas extras.
    filme_titulo = serializers.CharField(source="filme.titulo", read_only=True)
    filme_poster_url = serializers.CharField(source="filme.poster_url", read_only=True)
    filme_detalhe = FilmeSerializer(source="filme", read_only=True)
    # Para escrever, envie "sugerido_por" com uma lista de ids de amigos.
    # Para exibir (apelido + ícone), use "sugerido_por_detalhe".
    sugerido_por_detalhe = AmigoSerializer(
        source="sugerido_por", many=True, read_only=True
    )
    ano_do_grupo = serializers.IntegerField(read_only=True)
    # Alternativa a "filme": o id do título no TMDB e o seu tipo ("filme" ou "serie",
    # padrão "filme"). O título é buscado e salvo na hora.
    tmdb_id = serializers.IntegerField(write_only=True, required=False, min_value=1)
    tipo = serializers.ChoiceField(choices=Tipo.choices, write_only=True, required=False)
    pode_editar = serializers.SerializerMethodField()

    class Meta:
        model = Sessao
        fields = (
            "id",
            "filme",
            "tmdb_id",
            "tipo",
            "filme_titulo",
            "filme_poster_url",
            "filme_detalhe",
            "sugerido_por",
            "sugerido_por_detalhe",
            "ano",
            "ano_do_grupo",
            "data_exibicao",
            "tier",
            "pode_editar",
        )
        extra_kwargs = {"filme": {"required": False}, "ano": {"required": False}}

    @extend_schema_field(serializers.BooleanField())
    def get_pode_editar(self, obj):
        return _pode_editar(self.context, obj)

    def validate_sugerido_por(self, value):
        if not value:
            raise serializers.ValidationError(
                "Informe pelo menos um amigo que indicou o título."
            )
        return value

    def validate(self, attrs):
        # Em atualizações parciais (PATCH), usa o valor já salvo quando o campo não vem.
        instancia = self.instance
        erros = {}

        if instancia is None and not attrs.get("filme") and not attrs.get("tmdb_id"):
            erros["filme"] = "Informe o título (id) ou o tmdb_id."

        data = attrs.get("data_exibicao", getattr(instancia, "data_exibicao", None))
        ano = attrs.get("ano", getattr(instancia, "ano", None))
        tier = attrs.get("tier", getattr(instancia, "tier", None))
        usuario = getattr(self.context.get("request"), "user", None)

        if data is not None:
            # REGRA: com data, o ano é sempre o dela.
            if "ano" in attrs and attrs["ano"] != data.year:
                erros["ano"] = "O ano deve ser o mesmo da data de exibição."
            attrs["ano"] = data.year

        erros.update(
            erros_da_sessao(data, ano, tier, admin=usuario is not None and usuario.is_staff)
        )
        if erros:
            raise serializers.ValidationError(erros)
        return attrs

    def _resolver_filme(self, validated_data):
        tipo = validated_data.pop("tipo", Tipo.FILME)
        tmdb_id = validated_data.pop("tmdb_id", None)
        if tmdb_id:
            try:
                validated_data["filme"] = tmdb.obter_ou_criar_filme(tmdb_id, tipo)
            except tmdb.TMDBError as erro:
                raise serializers.ValidationError({"tmdb_id": str(erro)}) from erro

    def create(self, validated_data):
        self._resolver_filme(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._resolver_filme(validated_data)
        return super().update(instance, validated_data)


class FotoComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoComentario
        fields = ("id", "imagem")
        read_only_fields = ("imagem",)


class ComentarioSerializer(serializers.ModelSerializer):
    autor_apelido = serializers.CharField(source="autor.apelido", read_only=True)
    autor_icone_url = serializers.CharField(source="autor.icone_url", read_only=True)
    fotos = FotoComentarioSerializer(many=True, read_only=True)
    # Envio de fotos: use multipart/form-data e repita o campo "imagens" para cada arquivo.
    imagens = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    pode_editar = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = (
            "id",
            "sessao",
            "autor",
            "autor_apelido",
            "autor_icone_url",
            "texto",
            "criado_em",
            "fotos",
            "imagens",
            "pode_editar",
        )
        # O autor é sempre o usuário logado (definido na view), nunca vem do corpo.
        read_only_fields = ("autor", "criado_em")

    @extend_schema_field(serializers.BooleanField())
    def get_pode_editar(self, obj):
        return _pode_editar(self.context, obj)

    def validate_texto(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "O comentário deve ter pelo menos 2 caracteres."
            )
        return value

    def validate_sessao(self, sessao):
        # REGRA DE NEGÓCIO: não dá para comentar uma sessão que ainda não aconteceu.
        # (Sessão só com o ano é sempre do passado.)
        if sessao.data_exibicao and sessao.data_exibicao > timezone.localdate():
            raise serializers.ValidationError(
                "Não é possível comentar uma sessão que ainda não aconteceu."
            )
        return sessao

    def validate_imagens(self, arquivos):
        limite = settings.FOTO_TAMANHO_MAX_BYTES
        for arquivo in arquivos:
            if arquivo.size > limite:
                megas = limite / (1024 * 1024)
                raise serializers.ValidationError(
                    f"Cada foto pode ter no máximo {megas:g} MB."
                )
        return arquivos

    def validate(self, attrs):
        existentes = self.instance.fotos.count() if self.instance else 0
        novas = len(attrs.get("imagens", []))
        maximo = settings.COMENTARIO_MAX_FOTOS
        if existentes + novas > maximo:
            raise serializers.ValidationError(
                {"imagens": f"No máximo {maximo} fotos por comentário."}
            )
        if (
            self.instance
            and "sessao" in attrs
            and attrs["sessao"] != self.instance.sessao
        ):
            raise serializers.ValidationError(
                {"sessao": "Não é possível mudar a sessão de um comentário."}
            )
        return attrs

    def _anexar_fotos(self, comentario, imagens):
        for imagem in imagens:
            FotoComentario.objects.create(comentario=comentario, imagem=imagem)

    def create(self, validated_data):
        imagens = validated_data.pop("imagens", [])
        comentario = super().create(validated_data)
        self._anexar_fotos(comentario, imagens)
        return comentario

    def update(self, instance, validated_data):
        imagens = validated_data.pop("imagens", [])
        comentario = super().update(instance, validated_data)
        self._anexar_fotos(comentario, imagens)
        return comentario
