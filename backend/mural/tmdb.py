"""Cliente mínimo da API do TMDB (The Movie Database).

Busca filmes e séries e traz título, ano, diretor (ou criadores), gêneros, sinopse e
pôster em português. Os dados são gravados no nosso banco na primeira vez em que o
título é usado, então o site não depende do TMDB para funcionar depois disso.

Os dados e imagens vêm do TMDB; o frontend deve exibir o crédito no rodapé:
"This product uses the TMDB API but is not endorsed or certified by TMDB."
"""

import requests
from django.conf import settings

from .models import Filme

API = "https://api.themoviedb.org/3"
IMAGENS = "https://image.tmdb.org/t/p/w500"


class TMDBError(Exception):
    """Falha ao consultar o TMDB (sem chave, fora do ar, título inexistente...)."""


class TMDBChaveError(TMDBError):
    """O TMDB não aceitou a nossa chave: nenhuma consulta vai funcionar."""


def _get(caminho, **params):
    chave = settings.TMDB_API_KEY.strip()
    if not chave:
        raise TMDBError("A integração com o TMDB não está configurada.")

    headers = {}
    if chave.startswith("eyJ"):
        # "Token de leitura da API" (v4) vai no cabeçalho.
        headers["Authorization"] = f"Bearer {chave}"
    else:
        # Chave da API (v3) vai na URL.
        params["api_key"] = chave
    params.setdefault("language", "pt-BR")

    try:
        resposta = requests.get(
            f"{API}{caminho}", params=params, headers=headers, timeout=8
        )
    except requests.RequestException as erro:
        raise TMDBError("Não foi possível consultar o TMDB agora.") from erro

    if resposta.status_code == 401:
        raise TMDBChaveError("O TMDB recusou a chave de acesso.")
    if resposta.status_code == 404:
        raise TMDBError("Título não encontrado no TMDB.")
    if not resposta.ok:
        raise TMDBError("O TMDB recusou a consulta.")
    return resposta.json()


def _ano(data):
    """'1999-03-30' -> 1999 (ou None se não houver data)."""
    if data and data[:4].isdigit():
        return int(data[:4])
    return None


def _poster(caminho):
    return f"{IMAGENS}{caminho}" if caminho else ""


def _resumo(item, tipo):
    """Um resultado de busca (filme ou série) no formato que o frontend usa."""
    if tipo == "serie":
        titulo, original, data = item.get("name"), item.get("original_name"), item.get("first_air_date")
    else:
        titulo, original, data = item.get("title"), item.get("original_title"), item.get("release_date")
    return {
        "tipo": tipo,
        "tmdb_id": item["id"],
        "titulo": titulo or original or "",
        "titulo_original": original or "",
        "ano_lancamento": _ano(data),
        "sinopse": item.get("overview", ""),
        "poster_url": _poster(item.get("poster_path")),
    }


# Onde procurar cada tipo no TMDB: caminho da busca e nome do filtro de ano.
BUSCAS = {
    "filme": ("/search/movie", "year"),
    "serie": ("/search/tv", "first_air_date_year"),
}


def _pesquisar(texto, tipo, ano=None):
    """Resultados da busca de um tipo, como o TMDB devolve."""
    caminho, campo_ano = BUSCAS[tipo]
    params = {"query": texto, "include_adult": "false"}
    if ano:
        params[campo_ano] = ano
    return _get(caminho, **params).get("results", [])


def buscar(texto, ano=None):
    """Procura filmes e séries pelo título e devolve até 10 candidatos, os mais populares primeiro."""
    encontrados = [
        (item.get("popularity", 0), _resumo(item, tipo))
        for tipo in BUSCAS
        for item in _pesquisar(texto, tipo, ano)
    ]
    encontrados.sort(key=lambda par: par[0], reverse=True)
    return [resumo for _, resumo in encontrados[:10]]


def candidatos(texto, tipo, ano=None):
    """Todos os resultados de um só tipo, com a quantidade de votos (usado pelo importador)."""
    itens = sorted(
        _pesquisar(texto, tipo, ano), key=lambda item: item.get("popularity", 0), reverse=True
    )
    return [{**_resumo(item, tipo), "votos": item.get("vote_count", 0)} for item in itens]


def detalhes(tmdb_id, tipo="filme"):
    """Dados completos de um título, já nos campos do nosso model Filme."""
    if tipo == "serie":
        dados = _get(f"/tv/{tmdb_id}")
        titulo = dados.get("name") or dados.get("original_name", "")
        ano = _ano(dados.get("first_air_date"))
        # Séries não têm "o diretor": usamos os criadores.
        autores = [p["name"] for p in dados.get("created_by", [])]
    else:
        dados = _get(f"/movie/{tmdb_id}", append_to_response="credits")
        titulo = dados.get("title") or dados.get("original_title", "")
        ano = _ano(dados.get("release_date"))
        equipe = dados.get("credits", {}).get("crew", [])
        autores = [p["name"] for p in equipe if p.get("job") == "Director"]

    if ano is None:
        raise TMDBError("O TMDB não informa o ano deste título.")

    generos = [g["name"] for g in dados.get("genres", [])]
    return {
        "titulo": titulo[:150],
        "ano_lancamento": ano,
        "diretor": ", ".join(autores)[:150],
        "genero": ", ".join(generos)[:100],
        "sinopse": dados.get("overview", ""),
        "poster_url": _poster(dados.get("poster_path")),
    }


def obter_ou_criar_filme(tmdb_id, tipo="filme"):
    """Devolve o título com esse tipo e tmdb_id, buscando no TMDB só se ainda não existir."""
    filme = Filme.objects.filter(tipo=tipo, tmdb_id=tmdb_id).first()
    if filme is not None:
        return filme
    filme, _ = Filme.objects.get_or_create(
        tipo=tipo, tmdb_id=tmdb_id, defaults=detalhes(tmdb_id, tipo)
    )
    return filme
