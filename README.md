# Noite do Filme

Mural de filmes e séries com tier lists anuais, feito para um grupo de amigos que assiste a um título por semana e decide em conjunto a tier de cada um: **S, A, B, C ou VTNC**.

Projeto final de Desenvolvimento Web II (Bacharelado em Sistemas de Informação, IFC Araquari), com API em Django REST Framework e site em React.

| | Endereço |
| - | -------- |
| Site | https://www.noitedofilme.site |
| API | https://tierlistndf-production.up.railway.app/api/ |
| Documentação da API (Swagger) | https://tierlistndf-production.up.railway.app/api/docs/ |
| Código | https://github.com/estelista/tierlist_ndf |

## O que o site faz

- **Mural**: abas Ano 1, 2 e 3 (o grupo começou em 2024), cada uma com a tier list do ano, de S a VTNC, com as capas lado a lado e os ícones de quem indicou cada título.
- **Próximas sessões**: os títulos já agendados, no topo da página.
- **Detalhes**: ao clicar em uma capa, ficha do título (ano, gênero, direção, sinopse), data da sessão, quem indicou, outras vezes em que o grupo viu o mesmo título e os comentários.
- **Contas**: cadastro com código de convite do grupo; a conta só entra depois de aprovada pela administradora.
- **Para quem está logado**: cadastrar ou agendar sessões com busca de títulos no TMDB, comentar com até 4 fotos e editar o que criou.

Visitantes veem o mural, as tier lists e os detalhes; comentários e fotos são só para o grupo.

## Domínio

Uma **sessão** é um título exibido ao grupo, indicado por um ou mais amigos, com a tier decidida em conjunto.

| Entidade | Campos principais |
| -------- | ----------------- |
| `Amigo` | `apelido` (único), `icone_url`, `user` (conta de login) |
| `Filme` (os títulos: filmes e séries) | `tipo`, `tmdb_id`, `titulo`, `ano_lancamento`, `diretor`, `genero`, `sinopse`, `poster_url` |
| `Sessao` | `filme`, `sugerido_por` (um ou mais amigos), `ano`, `data_exibicao` (opcional), `tier`, `criado_por` |
| `Comentario` | `sessao`, `autor`, `texto`, `criado_em` |
| `FotoComentario` | `comentario`, `imagem` |

### Regras de negócio

- Sessão que já aconteceu precisa ter tier; sessão agendada (data futura) não pode ter.
- Com data, o `ano` é o da data. Sem data (o histórico dos dois primeiros anos), só a administradora cadastra, e só de anos anteriores.
- Nenhuma sessão antes de 2024; uma sessão por data; pelo menos um amigo indicador.
- Só se comenta sessão que já aconteceu; no máximo 4 fotos de até 5 MB, só imagens válidas.
- As tiers são ordenadas por ranking (S > A > B > C > VTNC), não em ordem alfabética.
- Cada amigo altera e apaga só o que criou; a administradora pode tudo.

## Principais endpoints

| Recurso | URL |
| ------- | --- |
| Sessões (CRUD, filtros, busca, ordenação e paginação) | `/api/sessoes/` |
| Tier lists por ano | `/api/sessoes/tier-lists/?ano=2026` |
| Abas de ano | `/api/sessoes/anos/` |
| Próximas sessões | `/api/sessoes/proximas/` |
| Títulos e amigos | `/api/filmes/`, `/api/amigos/` |
| Comentários com fotos | `/api/comentarios/` |
| Busca no TMDB | `/api/tmdb/buscar/?q=matrix` |
| Cadastro, login (JWT), renovação | `/api/auth/registro/`, `/api/auth/login/`, `/api/auth/refresh/` |
| Aprovação de contas | `/api/cadastros/` |

A lista completa, com parâmetros e exemplos, está no [README da API](backend/README.md#endpoints) e no Swagger.

## Tecnologias

- **API** (`backend/`): Python, Django, Django REST Framework, SimpleJWT, django-filter, drf-spectacular, Pillow; SQLite em desenvolvimento e PostgreSQL em produção; 103 testes automatizados.
- **Site** (`frontend/`): React 19, Vite e react-router, com CSS próprio.
- **Hospedagem**: API no Railway, site na Vercel.
- Dados e capas dos títulos: [TMDB](https://www.themoviedb.org/).

## Como rodar no computador

API (precisa de Python 3.10+ e [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py loaddata exemplo   # dados fictícios de exemplo
uv run python manage.py createsuperuser
uv run python manage.py runserver
uv run python manage.py test
```

Site (precisa de Node 22+), em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

O site abre em http://localhost:5173 e conversa com a API em http://127.0.0.1:8000. Em desenvolvimento, o código de convite é `convite-dev`; para buscar títulos, defina a variável `TMDB_API_KEY` antes de rodar a API.

Mais detalhes: [README da API](backend/README.md) (variáveis de ambiente, importação do histórico, publicação no Railway) e [README do site](frontend/README.md).

## Conta de teste

O mural e os detalhes podem ser vistos sem login. Para testar as funções do grupo no site publicado, peça uma conta de teste à autora; para testar localmente, crie uma com `createsuperuser` (comando acima). Nenhuma senha ou chave real fica neste repositório.

## Estrutura

```
├── backend/       # API Django (config/ e app mural/)
└── frontend/       # site React (src/componentes, src/paginas)
```

---

This product uses the TMDB API but is not endorsed or certified by TMDB.
