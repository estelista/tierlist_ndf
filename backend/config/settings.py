"""Configurações do projeto noitedofilme."""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def lista_do_ambiente(nome, padrao=""):
    """Lê uma variável de ambiente com valores separados por vírgula."""
    return [item.strip() for item in os.environ.get(nome, padrao).split(",") if item.strip()]


# Em desenvolvimento os padrões abaixo bastam. No deploy, defina as variáveis de ambiente
# SECRET_KEY, DEBUG=0, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CODIGO_CONVITE e TMDB_API_KEY;
# na hospedagem com proxy, também CSRF_TRUSTED_ORIGINS, NUM_PROXIES e, se houver, DATABASE_URL.
DEBUG = os.environ.get("DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-apenas-para-desenvolvimento")
if not DEBUG and SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured("Defina a variável de ambiente SECRET_KEY em produção.")
ALLOWED_HOSTS = lista_do_ambiente("ALLOWED_HOSTS")
# Endereços https do próprio servidor, para o login do /admin/ funcionar atrás do proxy.
CSRF_TRUSTED_ORIGINS = lista_do_ambiente("CSRF_TRUSTED_ORIGINS")
if not DEBUG:
    # O proxy da hospedagem atende em https e repassa em http; este cabeçalho avisa o Django.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "mural",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serve os arquivos do collectstatic (estilos do admin e do Swagger) em produção.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite em desenvolvimento; com DATABASE_URL (ex.: PostgreSQL do Railway), usa esse banco.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        # Testa a conexão antes de reaproveitar: se o banco reiniciou, abre outra em vez de dar erro.
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Nos testes, um hash de senha mais simples (e rápido). Nunca vale fora dos testes.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Destino do collectstatic (estilos do admin e do Swagger), servido pela hospedagem.
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Fotos enviadas nos comentários. Em produção, o disco precisa ser permanente: no Railway,
# use um volume e aponte MEDIA_ROOT para ele.
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Por padrão qualquer um lê e só quem está logado escreve; cada recurso refina isso.
    "DEFAULT_PERMISSION_CLASSES": [
        "mural.permissions.LeituraPublicaEscritaAutenticada",
    ],
    # Limites só nos pontos sensíveis (cada view declara o seu throttle_scope).
    "DEFAULT_THROTTLE_RATES": {
        "registro": "5/hour",
        "login": "10/minute",
        "tmdb": "60/minute",
    },
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "mural.pagination.PaginacaoPadrao",
    "PAGE_SIZE": 12,
    # Atrás de proxy, quantos proxies há na frente, para os limites de tentativas usarem o IP
    # de quem acessa (e não o do proxy). Vazio = sem proxy (desenvolvimento).
    "NUM_PROXIES": int(os.environ["NUM_PROXIES"]) if os.environ.get("NUM_PROXIES") else None,
}

# Ano em que o grupo começou: 2024 é o "Ano 1", 2025 o "Ano 2" e assim por diante.
ANO_INICIO_GRUPO = 2024

# Código que a administradora passa aos amigos para liberar o cadastro de contas.
# Vazio = cadastro desligado. Em desenvolvimento usa um valor de teste.
CODIGO_CONVITE = os.environ.get("CODIGO_CONVITE", "convite-dev" if DEBUG else "")

# Chave da API do TMDB (https://www.themoviedb.org/settings/api). Sem ela, a busca
# automática de filmes fica desligada, mas o resto do sistema funciona.
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")

# Origens do frontend autorizadas a chamar a API (CORS). Padrão: servidor do Vite.
CORS_ALLOWED_ORIGINS = lista_do_ambiente(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

# Login por token (JWT): o de acesso dura pouco; o de renovação evita logar toda hora.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

# Limites das fotos dos comentários.
COMENTARIO_MAX_FOTOS = 4
FOTO_TAMANHO_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

SPECTACULAR_SETTINGS = {
    "TITLE": "Noite do Filme API",
    "DESCRIPTION": "Mural de filmes e tier lists anuais de um grupo de amigos.",
    "VERSION": "0.2.0",
    # Separa os schemas de envio e de resposta (necessário para o upload de fotos).
    "COMPONENT_SPLIT_REQUEST": True,
}
