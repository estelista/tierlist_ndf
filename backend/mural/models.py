from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Tier(models.TextChoices):
    """Tiers da tier list, da mais alta para a mais baixa."""

    S = "S", "S"
    A = "A", "A"
    B = "B", "B"
    C = "C", "C"
    VTNC = "VTNC", "VTNC"


# Posição de cada tier no ranking (maior = melhor). Usado para ordenar,
# já que ordenar o texto alfabeticamente colocaria VTNC no meio.
TIER_RANK = {"S": 5, "A": 4, "B": 3, "C": 2, "VTNC": 1}


class Tipo(models.TextChoices):
    """O grupo também assiste a séries curtas, que entram no mural como qualquer título."""

    FILME = "filme", "Filme"
    SERIE = "serie", "Série"


class Amigo(models.Model):
    """Participante do grupo. Fica ligado a um usuário de login quando a conta é aprovada."""

    apelido = models.CharField(max_length=50, unique=True)
    # Endereço da imagem do ícone desenhado para o amigo (ex.: /icones/ana.png,
    # guardado junto do frontend, ou uma URL externa).
    icone_url = models.CharField(max_length=300, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amigo",
    )

    class Meta:
        ordering = ["apelido"]

    def __str__(self):
        return self.apelido


class Filme(models.Model):
    """Título do catálogo (filme ou série). Pode ter várias sessões (o grupo pode rever)."""

    tipo = models.CharField(max_length=5, choices=Tipo.choices, default=Tipo.FILME)
    # Identificador no TMDB (The Movie Database), de onde vêm sinopse, gêneros e pôster.
    # O número de um filme e o de uma série podem coincidir, então o que é único
    # é o par (tipo, tmdb_id).
    tmdb_id = models.PositiveIntegerField(null=True, blank=True)
    titulo = models.CharField(max_length=150)
    # Ano de lançamento (nas séries, o ano de estreia).
    ano_lancamento = models.PositiveSmallIntegerField()
    # Diretor (nas séries, os criadores).
    diretor = models.CharField(max_length=150, blank=True)
    genero = models.CharField(max_length=100, blank=True)
    sinopse = models.TextField(blank=True)
    poster_url = models.URLField(max_length=300, blank=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "título"
        verbose_name_plural = "títulos"
        constraints = [
            models.UniqueConstraint(fields=["tipo", "tmdb_id"], name="tmdb_unico_por_tipo")
        ]

    def __str__(self):
        return f"{self.titulo} ({self.ano_lancamento})"


class Sessao(models.Model):
    """Uma exibição de um filme para o grupo, com a tier definida em conjunto.

    Nos anos 1 e 2 só o ano foi guardado: ``data_exibicao`` fica vazia e ``ano`` diz
    em que ano a sessão aconteceu. Quando há data, o ano é sempre o dela.
    """

    filme = models.ForeignKey(
        Filme, on_delete=models.PROTECT, related_name="sessoes", verbose_name="título"
    )
    # Normalmente uma pessoa indica, mas a escolha pode ser feita em conjunto.
    sugerido_por = models.ManyToManyField(Amigo, related_name="sugestoes")
    ano = models.PositiveSmallIntegerField(
        blank=True, help_text="Preenchido automaticamente quando há data de exibição."
    )
    data_exibicao = models.DateField(unique=True, null=True, blank=True)
    # Nula só enquanto a sessão ainda não aconteceu (sessão agendada).
    tier = models.CharField(max_length=4, choices=Tier.choices, null=True, blank=True)
    # Quem cadastrou a sessão no site (só ele e a administradora podem alterá-la).
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessoes_criadas",
    )

    class Meta:
        ordering = ["-ano", "-data_exibicao"]
        verbose_name_plural = "sessões"

    def __str__(self):
        return f"{self.data_exibicao or self.ano} - {self.filme.titulo}"

    def clean(self):
        # Chamado pelo Django Admin: deduz o ano da data, ou exige um dos dois.
        if self.data_exibicao:
            self.ano = self.data_exibicao.year
        elif not self.ano:
            raise ValidationError("Informe a data ou o ano da sessão.")

    def save(self, *args, **kwargs):
        if self.data_exibicao:
            self.ano = self.data_exibicao.year
        super().save(*args, **kwargs)

    @property
    def ano_do_grupo(self):
        """2024 = Ano 1, 2025 = Ano 2, 2026 = Ano 3..."""
        return self.ano - settings.ANO_INICIO_GRUPO + 1

    @property
    def dono_id(self):
        return self.criado_por_id


class Comentario(models.Model):
    sessao = models.ForeignKey(
        Sessao, on_delete=models.CASCADE, related_name="comentarios"
    )
    autor = models.ForeignKey(
        Amigo, on_delete=models.CASCADE, related_name="comentarios"
    )
    texto = models.TextField(max_length=1000)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.autor} em {self.sessao}"

    @property
    def dono_id(self):
        return self.autor.user_id


class FotoComentario(models.Model):
    """Foto anexada a um comentário (um comentário pode ter várias)."""

    comentario = models.ForeignKey(
        Comentario, on_delete=models.CASCADE, related_name="fotos"
    )
    imagem = models.ImageField(upload_to="comentarios/%Y/%m/")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "foto de comentário"
        verbose_name_plural = "fotos de comentários"

    def __str__(self):
        return f"Foto {self.pk} do comentário {self.comentario_id}"

    @property
    def dono_id(self):
        return self.comentario.autor.user_id


@receiver(post_delete, sender=FotoComentario)
def apagar_arquivo_da_foto(sender, instance, **kwargs):
    """Remove o arquivo do disco quando a foto é apagada (inclusive em cascata)."""
    if instance.imagem:
        instance.imagem.delete(save=False)
