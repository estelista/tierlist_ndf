# Noite do Filme: frontend

Site do mural (React + Vite), que consome a API Django da pasta `backend`.

## Como rodar

Requisitos: Node 22 ou mais novo e a API rodando em `http://127.0.0.1:8000`.

```bash
npm install
npm run dev
```

O site abre em http://localhost:5173. Em desenvolvimento, o Vite repassa `/api` e `/media` para o Django, então não é preciso configurar nada.

| Comando | O que faz |
| ------- | --------- |
| `npm run dev` | servidor de desenvolvimento, na porta 5173 |
| `npm run celular` | o mesmo, acessível por outros aparelhos da mesma rede (o endereço aparece no terminal) |
| `npm run build` | gera o site em `dist/` |
| `npm run preview` | serve a pasta `dist/` (só funciona com `VITE_API_URL` definida no build) |
| `npm run lint` | verifica o código |

Para usar outro backend em desenvolvimento, defina `API_ALVO` (ex.: `http://127.0.0.1:8001`).

## Publicação

- Defina `VITE_API_URL` com o endereço da API (sem barra no final) na hora do build. Veja `.env.example`.
- Na API, inclua o endereço do site em `CORS_ALLOWED_ORIGINS`.
- As páginas têm endereço próprio (`/ano/2`, `/entrar`), então a hospedagem precisa devolver o `index.html` para qualquer caminho (regra de "SPA").

## Ícones dos amigos

Os desenhos ficam em `public/icones/` e o endereço (ex.: `/icones/ana.png`) vai no `icone_url` do amigo: na aprovação da conta ou no `/admin/` do Django. Quem não tem ícone aparece com a inicial do apelido.

## Páginas

| Endereço | O que mostra | Quem acessa |
| -------- | ------------ | ----------- |
| `/` e `/ano/N` | próximas sessões, abas dos anos e tier list | todos |
| `?sessao=ID` (em qualquer ano) | detalhes de uma sessão; comentários e fotos só para logados | todos |
| `/entrar`, `/cadastro` | login e pedido de conta com código de convite | todos |
| `/nova-sessao`, `/sessoes/ID/editar` | cadastrar, agendar ou alterar uma sessão, com busca no TMDB | amigos |
| `/contas` | aprovar ou recusar pedidos de conta | administradora |

## Estrutura

```
src/
├── api.js          # chamadas à API, renovação do login, mensagens de erro
├── sessao.js       # login guardado no navegador
├── useDados.js     # leitura da API nos componentes
├── textos.js       # nomes, datas, gêneros e crédito do TMDB
├── index.css       # cores e base
├── App.css         # componentes
├── componentes/
└── paginas/
```

O nome do site e o da tier list ficam em `src/textos.js`.
