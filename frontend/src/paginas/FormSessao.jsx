import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { api } from '../api.js'
import Aviso from '../componentes/Aviso.jsx'
import Campo from '../componentes/Campo.jsx'
import EscolhaTitulo from '../componentes/EscolhaTitulo.jsx'
import LetraTier from '../componentes/LetraTier.jsx'
import Icone from '../componentes/Icone.jsx'
import { useUsuario } from '../sessao.js'
import { NOME_DO_SITE, TIERS, hoje } from '../textos.js'
import { useDados } from '../useDados.js'
import NaoEncontrado from './NaoEncontrado.jsx'
import PedirLogin from './PedirLogin.jsx'

// Mensagens da API trocadas por outras que dizem o que fazer.
function erroDaData(texto) {
  return texto && /já existe|already exists/i.test(texto)
    ? 'Já existe uma sessão nessa data. Escolha outra.'
    : texto
}

function Formulario({ sessao, amigos, anos, usuario }) {
  const navegar = useNavigate()
  const formulario = useRef(null)
  const anosPassados = anos.anos.map((aba) => aba.ano).filter((ano) => ano < anos.ano_atual)
  const podeSoAno = usuario.is_admin && anosPassados.length > 0

  const [titulo, setTitulo] = useState(sessao?.filme_detalhe ?? null)
  const [indicadores, setIndicadores] = useState(
    sessao?.sugerido_por ?? (usuario.amigo_id ? [usuario.amigo_id] : []),
  )
  const [soAno, setSoAno] = useState(Boolean(sessao) && !sessao.data_exibicao)
  const [data, setData] = useState(sessao?.data_exibicao ?? (sessao ? '' : hoje()))
  const [ano, setAno] = useState(
    sessao && !sessao.data_exibicao ? sessao.ano : anosPassados.at(-1),
  )
  const [tier, setTier] = useState(sessao?.tier ?? '')
  const [erros, setErros] = useState({})
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const futura = !soAno && data > hoje()

  function mostrarErros(campos) {
    setErros(campos)
    // Leva a pessoa ao primeiro campo com problema.
    requestAnimationFrame(() => {
      const alvo = formulario.current?.querySelector('.campo-erro')
      alvo?.scrollIntoView({ block: 'center' })
    })
  }

  function conferir() {
    const campos = {}
    if (!titulo) campos.titulo = 'Escolha o título.'
    if (indicadores.length === 0) campos.sugerido_por = 'Marque quem indicou o título.'
    if (!soAno && !data) campos.data_exibicao = 'Informe a data da sessão.'
    if (!futura && !tier) campos.tier = 'Escolha a tier. Só sessão com data futura fica sem.'
    return campos
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErro(null)
    const faltando = conferir()
    if (Object.keys(faltando).length > 0) {
      mostrarErros(faltando)
      return
    }
    setErros({})

    const corpo = {
      sugerido_por: indicadores,
      data_exibicao: soAno ? null : data,
      tier: futura ? null : tier,
    }
    if (soAno) corpo.ano = Number(ano)
    if (titulo.id) corpo.filme = titulo.id
    else Object.assign(corpo, { tmdb_id: titulo.tmdb_id, tipo: titulo.tipo })

    setEnviando(true)
    try {
      const salva = sessao
        ? await api(`/sessoes/${sessao.id}/`, { metodo: 'PATCH', corpo })
        : await api('/sessoes/', { metodo: 'POST', corpo })
      const atual = salva.ano === anos.ano_atual || salva.ano_do_grupo > anos.anos.length
      navegar(`${atual ? '/' : `/ano/${salva.ano_do_grupo}`}?sessao=${salva.id}`, {
        replace: true,
        state: { sessao: salva },
      })
    } catch (falha) {
      const { filme, tmdb_id, tipo, sugerido_por, data_exibicao, ano: erroAno, tier: erroTier } = falha.campos ?? {}
      const campos = {
        titulo: filme ?? tmdb_id ?? tipo,
        sugerido_por,
        data_exibicao: erroDaData(data_exibicao ?? (soAno ? undefined : erroAno)),
        ano: soAno ? erroAno : undefined,
        tier: erroTier,
      }
      mostrarErros(campos)
      if (!Object.values(campos).some(Boolean)) setErro(falha)
      setEnviando(false)
    }
  }

  function alternar(id) {
    setIndicadores(
      indicadores.includes(id) ? indicadores.filter((outro) => outro !== id) : [...indicadores, id],
    )
  }

  return (
    <form ref={formulario} onSubmit={enviar} noValidate>
      <EscolhaTitulo valor={titulo} aoEscolher={setTitulo} erro={erros.titulo} />

      <fieldset className="campo">
        <legend>Indicado por</legend>
        <div className="opcoes">
          {amigos.map((amigo) => (
            <label key={amigo.id} className="opcao-botao">
              <input
                type="checkbox"
                checked={indicadores.includes(amigo.id)}
                onChange={() => alternar(amigo.id)}
              />
              <Icone amigo={amigo} />
              {amigo.apelido}
            </label>
          ))}
        </div>
        {erros.sugerido_por && <p className="campo-erro">{erros.sugerido_por}</p>}
      </fieldset>

      {soAno ? (
        <Campo rotulo="Ano" erro={erros.ano}>
          {(ligacoes) => (
            <select {...ligacoes} value={ano} onChange={(e) => setAno(e.target.value)}>
              {anosPassados.map((opcao) => (
                <option key={opcao}>{opcao}</option>
              ))}
            </select>
          )}
        </Campo>
      ) : (
        <Campo
          rotulo="Data"
          erro={erros.data_exibicao}
          ajuda="Use uma data futura para agendar a sessão."
        >
          {(ligacoes) => (
            <input
              {...ligacoes}
              type="date"
              min={`${anos.anos[0].ano}-01-01`}
              value={data}
              onChange={(e) => setData(e.target.value)}
            />
          )}
        </Campo>
      )}
      {podeSoAno && (
        <label className="opcao">
          <input type="checkbox" checked={soAno} onChange={(e) => setSoAno(e.target.checked)} />
          Só sei o ano
        </label>
      )}

      {futura ? (
        <p className="nota">A tier entra depois que a sessão acontecer.</p>
      ) : (
        <fieldset className="campo">
          <legend>Tier</legend>
          <div className="opcoes">
            {TIERS.map((opcao) => (
              <label key={opcao} className="opcao-tier" data-tier={opcao}>
                <input
                  type="radio"
                  name="tier"
                  checked={tier === opcao}
                  onChange={() => setTier(opcao)}
                />
                <LetraTier tier={opcao} />
              </label>
            ))}
          </div>
          {erros.tier && <p className="campo-erro">{erros.tier}</p>}
        </fieldset>
      )}

      <Aviso erro={erro} />
      <div className="acoes">
        <button type="submit" className="botao" disabled={enviando}>
          {sessao ? 'Salvar sessão' : futura ? 'Agendar sessão' : 'Cadastrar sessão'}
        </button>
        <Link to="/" className="link">
          Cancelar
        </Link>
      </div>
    </form>
  )
}

export default function FormSessao() {
  const { id } = useParams()
  const usuario = useUsuario()
  const nome = id ? 'Alterar sessão' : 'Cadastrar sessão'
  const amigos = useDados(usuario ? '/amigos/' : null, { todas: true })
  const anos = useDados(usuario ? '/sessoes/anos/' : null)
  const sessao = useDados(usuario && id ? `/sessoes/${encodeURIComponent(id)}/` : null)

  if (!usuario) return <PedirLogin titulo={nome} />
  if (sessao.erro?.status === 404) return <NaoEncontrado texto="Esta sessão não existe." />
  if (sessao.dados && !sessao.dados.pode_editar) {
    return <NaoEncontrado texto="Só quem cadastrou a sessão (ou a administradora) pode alterar." />
  }

  const pronto = amigos.dados && anos.dados && (!id || sessao.dados)
  const falhou = [amigos, anos, sessao].find((leitura) => leitura.erro)
  return (
    <div className="pagina pagina-estreita">
      <title>{`${nome} | ${NOME_DO_SITE}`}</title>
      <h1>{nome}</h1>
      {falhou && !pronto && <Aviso erro={falhou.erro} tentar={falhou.recarregar} />}
      {pronto && (
        <Formulario
          key={`${usuario.id}-${id}`}
          sessao={id ? sessao.dados : null}
          amigos={amigos.dados}
          anos={anos.dados}
          usuario={usuario}
        />
      )}
    </div>
  )
}
