// Textos e formatos usados em várias telas.

export const NOME_DO_SITE = 'Noite do Filme'
export const NOME_DA_LISTA = 'Tier List dos Bandidos'
export const CREDITO_TMDB =
  'This product uses the TMDB API but is not endorsed or certified by TMDB.'

export const TIERS = ['S', 'A', 'B', 'C', 'VTNC']

// As datas da API vêm como "2026-11-21", sem hora: montadas por partes para não
// voltarem um dia por causa do fuso.
function dataLocal(iso) {
  const [ano, mes, dia] = iso.split('-').map(Number)
  return new Date(ano, mes - 1, dia)
}

const formatoLongo = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})
const formatoCurto = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})
const formatoMomento = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'medium', timeStyle: 'short' })
// O formato sueco é AAAA-MM-DD, o mesmo da API.
const formatoHoje = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' })

export const dataPorExtenso = (iso) => formatoLongo.format(dataLocal(iso))
export const momento = (iso) => formatoMomento.format(new Date(iso))

/** Hoje (AAAA-MM-DD) no fuso da API, que decide se uma sessão já aconteceu. */
export const hoje = () => formatoHoje.format(new Date())

export function ontem() {
  const data = dataLocal(hoje())
  data.setDate(data.getDate() - 1)
  const dois = (n) => String(n).padStart(2, '0')
  return `${data.getFullYear()}-${dois(data.getMonth() + 1)}-${dois(data.getDate())}`
}

/** "Hoje", "Amanhã" ou "Sábado, 28 de novembro". */
export function diaDaSessao(iso) {
  const dias = Math.round((dataLocal(iso) - dataLocal(hoje())) / 86400000)
  if (dias === 0) return 'Hoje'
  if (dias === 1) return 'Amanhã'
  const texto = formatoCurto.format(dataLocal(iso))
  return texto[0].toUpperCase() + texto.slice(1)
}

export function quando(sessao) {
  return sessao.data_exibicao ? dataPorExtenso(sessao.data_exibicao) : String(sessao.ano)
}

/** "13 títulos", "1 título" */
export const contarTitulos = (n) => `${n} ${n === 1 ? 'título' : 'títulos'}`

export const nomeDoTipo = (tipo) => (tipo === 'serie' ? 'Série' : 'Filme')

// O TMDB não traduz alguns gêneros de séries.
const GENEROS = {
  'Action & Adventure': 'Ação e aventura',
  'Sci-Fi & Fantasy': 'Ficção científica e fantasia',
  'War & Politics': 'Guerra e política',
  Kids: 'Infantil',
  News: 'Notícias',
  Reality: 'Reality show',
  Soap: 'Novela',
  Talk: 'Entrevistas',
}

export function generos(texto) {
  return texto
    .split(', ')
    .map((genero) => GENEROS[genero] ?? genero)
    .join(', ')
}

/** Pôster do TMDB em outro tamanho (w185, w342, w500). Outras URLs ficam como estão. */
export function poster(url, largura) {
  return url.replace(/^(https:\/\/image\.tmdb\.org\/t\/p\/)w\d+\//, `$1${largura}/`)
}
