import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router'
import { api } from '../api.js'
import { generos, hoje, nomeDoTipo, quando } from '../textos.js'
import { useDados } from '../useDados.js'
import Aviso from './Aviso.jsx'
import BotaoConfirmar from './BotaoConfirmar.jsx'
import Capa from './Capa.jsx'
import { LinkSessao } from './CartaoSessao.jsx'
import Comentarios from './Comentarios.jsx'
import Icone from './Icone.jsx'
import LetraTier from './LetraTier.jsx'

function TambemExibido({ sessao }) {
  const { dados } = useDados(`/sessoes/?filme=${sessao.filme}`, { todas: true })
  const outras = dados?.filter((outra) => outra.id !== sessao.id) ?? []
  if (outras.length === 0) return null
  return (
    <section>
      <h3>Também exibido em</h3>
      <ul className="lista-simples">
        {outras.map((outra) => (
          <li key={outra.id}>
            <LinkSessao sessao={outra}>{quando(outra)}</LinkSessao>
            {outra.tier ? ` (Ano ${outra.ano_do_grupo}, tier ${outra.tier})` : ' (sem tier ainda)'}
          </li>
        ))}
      </ul>
    </section>
  )
}

function Conteudo({ sessao, aoApagar }) {
  const { filme_detalhe: titulo } = sessao
  const [erro, setErro] = useState(null)
  const agendada = sessao.data_exibicao !== null && sessao.data_exibicao > hoje()

  async function apagar() {
    setErro(null)
    try {
      await api(`/sessoes/${sessao.id}/`, { metodo: 'DELETE' })
      aoApagar()
    } catch (falha) {
      setErro(falha)
    }
  }

  return (
    <>
      <div className="detalhe-capa">
        <Capa titulo={titulo.titulo} url={titulo.poster_url} alt="" grande />
        <p className="detalhe-tier">
          {sessao.tier ? (
            <>
              <span className="so-leitor">Tier </span>
              <LetraTier tier={sessao.tier} />
            </>
          ) : (
            <span className="detalhe-sem-tier">{agendada ? 'Agendada' : 'Sem tier'}</span>
          )}
        </p>
      </div>

      <div className="detalhe-texto">
        <h2 id="detalhe-titulo">{titulo.titulo}</h2>
        <p className="detalhe-resumo">
          {nomeDoTipo(titulo.tipo)} de {titulo.ano_lancamento}
        </p>
        <dl className="ficha">
          {titulo.genero && (
            <>
              <dt>Gênero</dt>
              <dd>{generos(titulo.genero)}</dd>
            </>
          )}
          {titulo.diretor && (
            <>
              <dt>{titulo.tipo === 'serie' ? 'Criação' : 'Direção'}</dt>
              <dd>{titulo.diretor}</dd>
            </>
          )}
          <dt>{agendada ? 'Vai ser em' : 'Exibido em'}</dt>
          <dd>{quando(sessao)}</dd>
          <dt>Indicado por</dt>
          <dd className="ficha-amigos">
            {sessao.sugerido_por_detalhe.map((amigo) => (
              <span key={amigo.id} className="amigo">
                <Icone amigo={amigo} />
                {amigo.apelido}
              </span>
            ))}
          </dd>
        </dl>
        {titulo.sinopse && <p className="sinopse">{titulo.sinopse}</p>}

        {sessao.pode_editar && (
          <div className="acoes">
            <Link to={`/sessoes/${sessao.id}/editar`} className="link">
              {sessao.tier || agendada ? 'Alterar sessão' : 'Dar a tier'}
            </Link>
            <BotaoConfirmar
              pergunta="Apagar esta sessão e os comentários dela?"
              confirmar="Apagar"
              aoConfirmar={apagar}
            >
              Apagar sessão
            </BotaoConfirmar>
          </div>
        )}
        <Aviso erro={erro} />

        <TambemExibido sessao={sessao} />
        {agendada ? (
          <p className="nota">Os comentários abrem no dia da sessão.</p>
        ) : (
          <Comentarios sessao={sessao} />
        )}
      </div>
    </>
  )
}

/** Janela com os detalhes de uma sessão, aberta pelo endereço (?sessao=12). */
export default function DetalheSessao({ id, aoMudar }) {
  const dialogo = useRef(null)
  const fechando = useRef(false) // fecha uma vez só, mesmo com dois cliques seguidos
  const navegar = useNavigate()
  const { pathname, state } = useLocation()
  const { dados, erro, recarregar } = useDados(/^\d+$/.test(id) ? `/sessoes/${id}/` : null)

  // Vindo do mural, os dados do cartão já bastam para abrir sem espera.
  const doCartao = String(state?.sessao?.id) === id ? state.sessao : null
  const sessao = dados ?? doCartao
  const sumiu = erro?.status === 404 || !/^\d+$/.test(id)

  useEffect(() => {
    if (!dialogo.current.open) dialogo.current.showModal()
  }, [])

  function fechar() {
    if (fechando.current) return
    fechando.current = true
    if (state?.abertaNoSite) navegar(-1)
    else navegar(pathname, { replace: true })
  }

  return (
    <dialog
      ref={dialogo}
      className="detalhe"
      data-tier={sumiu ? undefined : (sessao?.tier ?? undefined)}
      aria-labelledby={sessao && !sumiu ? 'detalhe-titulo' : undefined}
      aria-label={sessao && !sumiu ? undefined : 'Detalhes da sessão'}
      onCancel={(evento) => {
        if (evento.target !== dialogo.current) return // "cancelar" da escolha de fotos
        evento.preventDefault()
        fechar()
      }}
      onClose={fechar}
      onMouseDown={(evento) => {
        if (evento.target === dialogo.current) fechar()
      }}
    >
      <div className="detalhe-corpo">
        <button
          type="button"
          className="fechar"
          aria-label="Fechar"
          onClick={fechar}
        >
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M3 3l10 10M13 3L3 13" />
          </svg>
        </button>
        {sumiu && <p className="detalhe-mensagem">Esta sessão não existe ou foi apagada.</p>}
        {!sumiu && erro && !sessao && (
          <div className="detalhe-mensagem">
            <Aviso erro={erro} tentar={recarregar} />
          </div>
        )}
        {!sumiu && !erro && !sessao && <p className="detalhe-mensagem">Carregando a sessão.</p>}
        {!sumiu && sessao && (
          <Conteudo
            sessao={sessao}
            aoApagar={() => {
              aoMudar()
              fechar()
            }}
          />
        )}
      </div>
    </dialog>
  )
}
