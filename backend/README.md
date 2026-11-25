# Noite do Filme

API REST de um mural de filmes com tier lists anuais, feita para um grupo de amigos que assiste a um filme por semana e avalia em conjunto numa tier list (S, A, B, C, VTNC).

Construída com Django e Django REST Framework. O site em React fica na pasta `frontend/` e consome esta API; a visão geral do projeto está no [README da raiz](../README.md).

## Domínio

Cada **sessão** é um título (filme ou série curta) exibido para o grupo, indicado por um ou mais amigos (a escolha pode ser em conjunto), que recebe uma tier definida pelo grupo. O mural mostra as sessões separadas por ano, uma tier list por ano. Os anos são contados a partir do início do grupo (2024 = Ano 1, 2025 = Ano 2, 2026 = Ano 3), configurável em `ANO_INICIO_GRUPO` no `config/settings.py`.

Nos anos 1 e 2 só o ano foi guardado, sem dia e mês. Por isso a sessão tem `ano` (sempre) e `data_exibicao` (opcional).

### Models

| Model | Campos principais |
| ----- | ----------------- |
| `Amigo` | `apelido` (único), `icone_url` (ícone desenhado do amigo), `user` (conta de login) |
| `Filme` (os títulos) | `tipo` (filme ou série), `tmdb_id` (único por tipo), `titulo`, `ano_lancamento`, `diretor` (criadores, nas séries), `genero`, `sinopse`, `poster_url` |
| `Sessao` | `filme`, `sugerido_por` (um ou mais amigos), `ano`, `data_exibicao` (única, opcional), `tier`, `criado_por` |
| `Comentario` | `sessao`, `autor`, `texto`, `criado_em` |
| `FotoComentario` | `comentario`, `imagem` |

Séries entram só pelo nome, quando o grupo termina de ver (sem temporada ou episódio). Um mesmo título pode ter várias sessões (o grupo pode rever), cada uma com sua tier, data e comentários.

### Regras de negócio

- Sessão que já aconteceu (data de hoje para trás, ou só com o ano) **precisa ter tier**. Sessão futura (agendada) **não pode ter**.
- Com data, o `ano` é sempre o da data. Sem data, só a administradora cadastra, e só de anos anteriores ao atual.
- Não existe sessão antes do início do grupo (`ANO_INICIO_GRUPO`).
- Só pode existir uma sessão por data.
- Toda sessão precisa de pelo menos um amigo que indicou o título.
- Só se comenta uma sessão que já aconteceu.
- Comentários têm no máximo 4 fotos de até 5 MB, e só imagens válidas são aceitas.
- A ordem das tiers é S > A > B > C > VTNC (ordenação por `tier_rank`, não alfabética).

### Quem pode o quê

| Ação | Visitante | Amigo aprovado | Administradora |
| ---- | :-------: | :------------: | :------------: |
| Ver mural, tier lists, títulos, amigos | ✔ | ✔ | ✔ |
| Ver comentários e fotos | | ✔ | ✔ |
| Cadastrar-se (com código de convite) | ✔ | | |
| Criar sessão (com tier, ou agendar) | | ✔ | ✔ |
| Alterar/apagar sessão | | só as que criou | todas |
| Comentar, com fotos | | ✔ (altera os seus) | ✔ (apaga qualquer) |
| Cadastrar sessão só com o ano (histórico) | | | ✔ |
| Aprovar/recusar contas, editar amigos e títulos | | | ✔ |

## Contas

1. O amigo pede cadastro em `POST /api/auth/registro/` com `apelido`, `senha` e o `codigo_convite` do grupo.
2. A conta nasce **pendente** (`is_active=False`) e não consegue entrar.
3. A administradora vê os pedidos em `GET /api/cadastros/` e aprova (`POST /api/cadastros/{id}/aprovar/`, com `icone_url` opcional) ou recusa (`.../recusar/`). Se já existir um amigo do histórico com o mesmo apelido, a conta é ligada a ele e o ícone é mantido.
4. Depois de aprovado, o login em `POST /api/auth/login/` (`username` e `password`, sem diferenciar maiúsculas) devolve `access` (30 min), `refresh` (30 dias) e os dados do usuário. As demais requisições enviam `Authorization: Bearer <access>`. Para renovar: `POST /api/auth/refresh/`.

Cadastro, login e busca no TMDB têm limite de tentativas (429 ao exceder).

## Como rodar

Requisitos: Python 3.10+ e [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py loaddata exemplo
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- API: http://127.0.0.1:8000/api/
- Swagger: http://127.0.0.1:8000/api/docs/
- Admin: http://127.0.0.1:8000/admin/

Para a administradora comentar, crie no `/admin/` um **Amigo** ligado ao seu usuário.

Testes (não usam a internet; o TMDB é simulado):

```bash
uv run python manage.py test
```

### Variáveis de ambiente

Em desenvolvimento nenhuma é obrigatória. No deploy, defina:

| Variável | Para quê | Padrão em desenvolvimento |
| -------- | -------- | ------------------------- |
| `SECRET_KEY` | chave secreta do Django (obrigatória com `DEBUG=0`) | chave de teste |
| `DEBUG` | `0` em produção | `1` |
| `ALLOWED_HOSTS` | domínios da API, separados por vírgula | vazio |
| `CORS_ALLOWED_ORIGINS` | endereços do frontend, separados por vírgula | `http://localhost:5173` |
| `CODIGO_CONVITE` | código que libera o cadastro (vazio = cadastro desligado) | `convite-dev` |
| `TMDB_API_KEY` | chave do [TMDB](https://www.themoviedb.org/settings/api) para buscar títulos | vazio (busca desligada) |

Exemplo (bash): `export TMDB_API_KEY="sua-chave"`. No PowerShell: `$env:TMDB_API_KEY="sua-chave"`.

Dados e imagens dos títulos vêm do TMDB; o frontend deve exibir no rodapé: *"This product uses the TMDB API but is not endorsed or certified by TMDB."*

### Importar o histórico

O comando `importar_historico` lê listas em CSV (UTF-8, separadas por `;`), busca cada título no TMDB e cria títulos, sessões e amigos. Precisa da `TMDB_API_KEY`.

```
ano;titulo;tipo;tier;indicado_por;data;ano_lancamento;tmdb_id
2024;Pulp Fiction;filme;S;Ana;;1994;
2025;Duna;filme;A;Beto+Caio;;2021;
2026;Matrix;filme;B;Beto;2026-04-05;;603
```

`data`, `ano_lancamento` (desempata títulos de mesmo nome) e `tmdb_id` (força um título) são opcionais. Anos anteriores ao atual podem ficar sem data.

```bash
uv run python manage.py importar_historico lista.csv --conferir   # não grava no banco
uv run python manage.py importar_historico lista.csv              # grava
```

A conferência mostra o que foi encontrado e pergunta, pelo número, qual é o título certo nos casos ambíguos; a escolha fica na coluna `tmdb_id` da lista (`--sem-perguntas` só mostra os casos). A importação grava tudo ou nada, e pode ser repetida: o que já está no site é pulado. Sessões importadas não têm dono, então só a administradora as altera.

## Publicação (Railway)

O Railway roda a API com PostgreSQL. O `railway.json` desta pasta já define o comando de início (migrações, `collectstatic` e gunicorn).

1. Em railway.com, entre com o GitHub e crie **New Project → Deploy from GitHub repo → tierlist_ndf**.
2. No serviço criado, **Settings → Root Directory**: `backend`.
3. No projeto, **New → Database → PostgreSQL**.
4. No serviço da API, **Volume** (botão direito no serviço → Attach volume), com Mount path `/data`. É onde ficam as fotos dos comentários.
5. **Settings → Networking → Generate Domain**: o endereço será algo como `ndf-api.up.railway.app`.
6. Em **Variables** do serviço da API (os valores secretos ficam só no Railway, nunca no GitHub):

   | Variável | Valor |
   | -------- | ----- |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `DEBUG` | `0` |
   | `SECRET_KEY` | uma frase longa e aleatória |
   | `ALLOWED_HOSTS` | o domínio do passo 5, sem `https://` |
   | `CSRF_TRUSTED_ORIGINS` | o domínio do passo 5, com `https://` |
   | `CORS_ALLOWED_ORIGINS` | o endereço do frontend, com `https://` |
   | `CODIGO_CONVITE` | o código do grupo |
   | `TMDB_API_KEY` | a chave do TMDB |
   | `NUM_PROXIES` | `1` |
   | `MEDIA_ROOT` | `/data/media` |

7. Teste `https://DOMINIO/api/sessoes/anos/`.

Para levar os dados do banco local, no PostgreSQL do Railway copie a **DATABASE_PUBLIC_URL** (aba Variables) e rode, na sua máquina:

```powershell
$env:PYTHONUTF8 = "1"   # no Windows, sem isso os acentos quebram
uv run python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e admin.logentry -e sessions -o ..\..\dados.json
$env:DATABASE_URL = "cole-a-DATABASE_PUBLIC_URL"
uv run python manage.py migrate
uv run python manage.py loaddata ..\..\dados.json
Remove-Item Env:DATABASE_URL, Env:PYTHONUTF8
```

O `dados.json` tem contas e apelidos reais: ele é gravado fora do repositório e deve ser apagado depois.

## Endpoints

| Recurso | URL | Observação |
| ------- | --- | ---------- |
| Sessões (recurso principal) | `/api/sessoes/` | CRUD completo |
| Tier lists por ano | `GET /api/sessoes/tier-lists/` | uma tabela por ano; `?ano=N` |
| Abas de ano | `GET /api/sessoes/anos/` | do Ano 1 até o atual, mais `ano_atual` |
| Próximas sessões | `GET /api/sessoes/proximas/` | de hoje em diante, sem tier |
| Títulos (filmes e séries) | `/api/filmes/` | leitura pública; escrita só da admin; `?tipo=serie` |
| Amigos | `/api/amigos/` | leitura pública; escrita só da admin |
| Comentários | `/api/comentarios/` | só logados |
| Apagar foto | `DELETE /api/fotos/{id}/` | dono ou admin |
| Buscar título no TMDB | `GET /api/tmdb/buscar/?q=matrix&ano=1999` | só logados; traz filmes e séries, cada um com seu `tipo` |
| Pedidos de cadastro | `/api/cadastros/` | só admin |
| Cadastro / login / renovar / eu | `/api/auth/registro/`, `login/`, `refresh/`, `eu/` | |

### Consulta de sessões

| Parâmetro | Exemplo | Descrição |
| --------- | ------- | --------- |
| `ano` | `?ano=2025` | Sessões de um ano (inclui as sem data exata) |
| `tier` | `?tier=S` | Sessões de uma tier |
| `sugerido_por` | `?sugerido_por=ana` | Por quem sugeriu |
| `titulo` | `?titulo=matrix` | Título contém o texto |
| `filme` | `?filme=3` | Todas as exibições de um título |
| `data_inicial`, `data_final` | `?data_inicial=2026-01-01` | Intervalo de datas |
| `avaliada` | `?avaliada=false` | Com ou sem tier |
| `search` | `?search=tarantino` | Busca em título, diretor e quem indicou |
| `ordering` | `?ordering=-tier_rank` | `data_exibicao`, `ano`, `tier_rank`, `filme__titulo` (`-` inverte) |
| `page`, `page_size` | `?page=2&page_size=6` | Paginação (máx. 100 por página) |

### Criar uma sessão (POST `/api/sessoes/`)

Com o título vindo do TMDB (ele é buscado e salvo na hora, uma única vez). Use `"tipo": "serie"` para séries; sem `tipo`, é filme:

```json
{
  "tmdb_id": 603,
  "sugerido_por": [2, 3],
  "data_exibicao": "2026-09-20",
  "tier": "A"
}
```

Ou com um título que já existe no catálogo: troque `tmdb_id` por `"filme": 1`. Para agendar uma sessão futura, omita o `tier`.

As respostas trazem `filme_detalhe` (sinopse, gênero, ano...), `sugerido_por_detalhe` (apelido e ícone de cada indicador), `ano_do_grupo` (2024 = 1) e `pode_editar` (se o usuário logado pode alterar aquela sessão).

### Comentar com fotos (POST `/api/comentarios/`)

Envie como `multipart/form-data`: `sessao`, `texto` e o campo `imagens` repetido para cada foto. O autor é sempre o usuário logado.

Códigos usados: `200`, `201`, `204`, `400` (validação ou regra de negócio), `401` (sem login), `403` (sem permissão), `404`, `429` (muitas tentativas) e `502` (TMDB indisponível).

## Estrutura

```
backend/
├── manage.py
├── pyproject.toml
├── config/            # configurações e rotas
└── mural/
    ├── models.py
    ├── serializers.py   # validações e regras de negócio
    ├── contas.py        # cadastro, login e aprovação de contas
    ├── permissions.py
    ├── tmdb.py          # busca de filmes e séries no TMDB
    ├── filters.py
    ├── views.py
    ├── pagination.py
    ├── admin.py
    ├── tests.py
    ├── management/commands/importar_historico.py
    └── fixtures/exemplo.json
```

## Publicado

- API: https://tierlistndf-production.up.railway.app/api/ (Swagger em `/api/docs/`)
- Site: https://www.noitedofilme.site
