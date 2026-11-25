"""Contas dos amigos: cadastro com código de convite, login (JWT) e aprovação.

Fluxo: o amigo se cadastra com o código do grupo -> a conta nasce INATIVA (pendente)
-> só a administradora aprova (e liga a conta ao ícone dele) -> aí o login funciona.
"""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import exceptions, mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Amigo
from .serializers import AmigoSerializer

User = get_user_model()


def dados_usuario(user):
    """Dados do usuário logado que o frontend precisa (nome, ícone, se é admin)."""
    amigo = getattr(user, "amigo", None)
    return {
        "id": user.id,
        "username": user.username,
        "apelido": amigo.apelido if amigo else user.username,
        "icone_url": amigo.icone_url if amigo else "",
        "amigo_id": amigo.id if amigo else None,
        "is_admin": user.is_staff,
    }


class UsuarioSerializer(serializers.Serializer):
    """Descreve a resposta de dados_usuario() (para a documentação)."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    apelido = serializers.CharField()
    icone_url = serializers.CharField()
    amigo_id = serializers.IntegerField(allow_null=True)
    is_admin = serializers.BooleanField()

    def to_representation(self, instance):
        return dados_usuario(instance)


# ---------------------------------------------------------------- cadastro


class RegistroSerializer(serializers.Serializer):
    apelido = serializers.CharField(max_length=50)
    senha = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )
    codigo_convite = serializers.CharField(write_only=True)

    def validate_codigo_convite(self, valor):
        esperado = settings.CODIGO_CONVITE
        if not esperado:
            raise serializers.ValidationError("O cadastro está indisponível no momento.")
        # compare_digest evita descobrir o código pelo tempo de resposta.
        if not secrets.compare_digest(valor.strip().encode(), esperado.encode()):
            raise serializers.ValidationError("Código de convite inválido.")
        return valor

    def validate_apelido(self, valor):
        valor = valor.strip()
        if len(valor) < 2:
            raise serializers.ValidationError(
                "O apelido deve ter pelo menos 2 caracteres."
            )
        em_uso = User.objects.filter(username__iexact=valor).exists()
        amigo_ocupado = Amigo.objects.filter(
            apelido__iexact=valor, user__isnull=False
        ).exists()
        if em_uso or amigo_ocupado:
            raise serializers.ValidationError("Este apelido já está em uso.")
        return valor

    def validate(self, attrs):
        try:
            validate_password(attrs["senha"], user=User(username=attrs["apelido"]))
        except DjangoValidationError as erro:
            raise serializers.ValidationError({"senha": list(erro.messages)}) from erro
        return attrs

    def create(self, validated_data):
        # is_active=False: a conta só funciona depois que a administradora aprovar.
        return User.objects.create_user(
            username=validated_data["apelido"],
            password=validated_data["senha"],
            is_active=False,
        )


class RegistroView(GenericAPIView):
    """Pede o cadastro de uma conta. Ela fica pendente até a administradora aprovar."""

    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registro"

    @extend_schema(responses={201: {"type": "object", "properties": {"detail": {"type": "string"}}}})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Cadastro enviado! Você poderá entrar assim que for aprovado."},
            status=201,
        )


# ------------------------------------------------------------------- login


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {"no_active_account": "Usuário ou senha incorretos."}

    def validate(self, attrs):
        campo = self.username_field
        usuario = User.objects.filter(
            **{f"{campo}__iexact": attrs.get(campo, "")}
        ).first()
        if usuario is not None:
            # Aceita "ana", "Ana" ou "ANA" (útil quando se digita no celular).
            attrs[campo] = getattr(usuario, campo)
            if not usuario.is_active and usuario.check_password(attrs.get("password", "")):
                raise exceptions.AuthenticationFailed(
                    "Sua conta ainda aguarda a aprovação da administradora.",
                    "conta_pendente",
                )
        dados = super().validate(attrs)
        dados["usuario"] = dados_usuario(self.user)
        return dados


class LoginView(TokenObtainPairView):
    """Troca usuário e senha por um token de acesso (access) e um de renovação (refresh)."""

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class EuView(GenericAPIView):
    """Dados do usuário logado."""

    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(dados_usuario(request.user))


# -------------------------------------------------- moderação (só a admin)


class CadastroPendenteSerializer(serializers.ModelSerializer):
    apelido = serializers.CharField(source="username", read_only=True)
    criado_em = serializers.DateTimeField(source="date_joined", read_only=True)
    amigo_existente = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "apelido", "criado_em", "amigo_existente")

    @extend_schema_field(serializers.BooleanField())
    def get_amigo_existente(self, usuario):
        """True se já existe um amigo com esse apelido (do histórico), que será ligado à conta."""
        return Amigo.objects.filter(
            apelido__iexact=usuario.username, user__isnull=True
        ).exists()


class AprovacaoSerializer(serializers.Serializer):
    icone_url = serializers.CharField(max_length=300, required=False, allow_blank=True)


class CadastroViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Pedidos de cadastro aguardando aprovação. Acesso só da administradora."""

    queryset = User.objects.filter(is_active=False, is_staff=False).order_by(
        "date_joined"
    )
    serializer_class = CadastroPendenteSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    @extend_schema(request=AprovacaoSerializer, responses=AmigoSerializer)
    @action(detail=True, methods=["post"])
    def aprovar(self, request, pk=None):
        """Ativa a conta e a liga a um amigo (reaproveita o do histórico, se existir)."""
        usuario = self.get_object()
        dados = AprovacaoSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        icone = dados.validated_data.get("icone_url", "").strip()

        with transaction.atomic():
            amigo = Amigo.objects.filter(
                apelido__iexact=usuario.username, user__isnull=True
            ).first() or Amigo(apelido=usuario.username)
            amigo.user = usuario
            if icone:
                amigo.icone_url = icone
            amigo.save()
            usuario.is_active = True
            usuario.save(update_fields=["is_active"])
        return Response(AmigoSerializer(amigo).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def recusar(self, request, pk=None):
        """Recusa o pedido: a conta pendente é apagada."""
        self.get_object().delete()
        return Response(status=204)
