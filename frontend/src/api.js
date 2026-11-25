// Conversa com a API: endereço, login por token (com renovação) e mensagens de erro.
import { encerrarSessao, lerSessao, salvarSessao } from './sessao.js'

// Vazio em desenvolvimento: as chamadas vão para o próprio Vite, que repassa ao Django.
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export class ErroApi extends Error {
  constructor(mensagem, status = 0, campos = {}) {
    super(mensagem)
    this.status = status
    this.campos = campos
  }
}

function emTexto(valor) {
  if (Array.isArray(valor)) return valor.map(emTexto).join(' ')
  if (valor && typeof valor === 'object') return Object.values(valor).map(emTexto).join(' ')
  return String(valor)
}

async function erroDaResposta(resposta) {
  const dados = await resposta.json().catch(() => null)
  const { status } = resposta
  if (status === 429) {
    return new ErroApi('Muitas tentativas seguidas. Espere um pouco e tente de novo.', status)
  }
  if (Array.isArray(dados)) return new ErroApi(emTexto(dados), status)
  if (dados && typeof dados === 'object') {
    const campos = {}
    for (const [campo, valor] of Object.entries(dados)) campos[campo] = emTexto(valor)
    const mensagem = campos.detail ?? campos.non_field_errors ?? 'Confira os campos indicados.'
    return new ErroApi(mensagem, status, campos)
  }
  return new ErroApi('O servidor não conseguiu responder. Tente de novo daqui a pouco.', status)
}

async function enviar(caminho, { metodo, corpo, signal, publica }) {
  const headers = { Accept: 'application/json' }
  const token = publica ? null : lerSessao()?.access
  if (token) headers.Authorization = `Bearer ${token}`
  let body
  if (corpo instanceof FormData) {
    body = corpo
  } else if (corpo !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(corpo)
  }
  try {
    return await fetch(`${BASE}/api${caminho}`, { method: metodo, headers, body, signal })
  } catch (erro) {
    if (erro.name === 'AbortError') throw erro
    throw new ErroApi('Sem conexão com o servidor. Confira a internet e tente de novo.')
  }
}

// Uma renovação por vez: se várias chamadas vencerem juntas, todas esperam a mesma.
let renovacao = null

async function pedirRenovacao() {
  const { refresh } = lerSessao()
  const resposta = await enviar('/auth/refresh/', {
    metodo: 'POST',
    corpo: { refresh },
    publica: true,
  })
  const atual = lerSessao()
  // Enquanto esperava, a pessoa saiu ou trocou de conta.
  if (atual?.refresh !== refresh) return atual !== null
  if (resposta.ok) {
    salvarSessao({ ...atual, ...(await resposta.json()) })
    return true
  }
  // Servidor com problema não é login vencido: mantém o login e avisa.
  if (resposta.status !== 401) throw await erroDaResposta(resposta)
  encerrarSessao()
  return false
}

function renovar() {
  renovacao ??= pedirRenovacao().finally(() => {
    renovacao = null
  })
  return renovacao
}

/** Chama a API e devolve o JSON (ou null, quando não há corpo). Lança ErroApi. */
export async function api(caminho, opcoes = {}) {
  const pedido = { metodo: 'GET', ...opcoes }
  const logado = !pedido.publica && lerSessao() !== null
  let resposta = await enviar(caminho, pedido)

  if (resposta.status === 401 && logado) {
    if (lerSessao() && (await renovar())) {
      resposta = await enviar(caminho, pedido)
      if (resposta.status === 401) encerrarSessao()
    }
    if (!lerSessao()) {
      // O login acabou: quem só estava lendo continua como visitante.
      if (pedido.metodo !== 'GET') {
        throw new ErroApi('Seu login expirou. Entre de novo para continuar.', 401)
      }
      resposta = await enviar(caminho, pedido)
    }
  }

  if (pedido.metodo !== 'GET') cache.clear()
  if (!resposta.ok) throw await erroDaResposta(resposta)
  return resposta.status === 204 ? null : resposta.json()
}

/** Junta todas as páginas de uma listagem paginada. */
export async function apiTudo(caminho, opcoes) {
  const separador = caminho.includes('?') ? '&' : '?'
  const itens = []
  for (let pagina = 1; ; pagina += 1) {
    const dados = await api(`${caminho}${separador}page_size=100&page=${pagina}`, opcoes)
    itens.push(...dados.results)
    if (!dados.next) return itens
  }
}

// Última resposta de cada leitura, para trocar de aba sem piscar. Toda escrita limpa.
export const cache = new Map()

// --- contas

export async function entrar(username, password) {
  const dados = await api('/auth/login/', {
    metodo: 'POST',
    corpo: { username, password },
    publica: true,
  })
  salvarSessao(dados)
}

/** Confere na abertura do site se o login guardado ainda vale e atualiza nome e ícone. */
export async function conferirLogin() {
  if (!lerSessao()) return
  try {
    const usuario = await api('/auth/eu/')
    const atual = lerSessao()
    if (atual) salvarSessao({ ...atual, usuario })
  } catch {
    // Sem internet: segue com o que está guardado.
  }
}

/** Endereço de uma foto enviada. Em desenvolvimento ela passa pelo Vite (funciona no celular). */
export function urlDaFoto(url) {
  if (!import.meta.env.DEV) return url
  return new URL(url, window.location.href).pathname
}
