import { useUsuario } from '../sessao.js'
import { dataPorExtenso, diaDaSessao, ontem } from '../textos.js'
import { useDados } from '../useDados.js'
import Aviso from './Aviso.jsx'
import Capa from './Capa.jsx'
import { Indicadores, LinkSessao } from './CartaoSessao.jsx'

function Lista({ sessoes, data }) {
  return (
    <ul className="proximas-lista">
      {sessoes.map((sessao) => (
        <li key={sessao.id} className="proxima">
          <LinkSessao sessao={sessao} className="proxima-capa" tabIndex={-1} aria-hidden="true">
            <Capa titulo={sessao.filme_titulo} url={sessao.filme_poster_url} />
          </LinkSessao>
          <div className="proxima-texto">
            <p className="proxima-data">{data(sessao.data_exibicao)}</p>
            <h3>
              <LinkSessao sessao={sessao}>{sessao.filme_titulo}</LinkSessao>
            </h3>
            <Indicadores sessao={sessao} />
          </div>
        </li>
      ))}
    </ul>
  )
}

/** Bloco fixo do mural: o que o grupo vai ver e, para os amigos, o que ficou sem tier. */
export default function Proximas() {
  const usuario = useUsuario()
  const { dados, erro, recarregar } = useDados('/sessoes/proximas/')
  // A sessão agendada some das próximas no dia seguinte; até ganhar tier, ela aparece aqui.
  const { dados: semTier } = useDados(
    usuario ? `/sessoes/?avaliada=false&data_final=${ontem()}&ordering=data_exibicao` : null,
    { todas: true },
  )

  return (
    <section className="proximas" aria-labelledby="proximas-titulo">
      <div>
        <h2 id="proximas-titulo">Próximas sessões</h2>
        {erro && <Aviso erro={erro} tentar={recarregar} />}
        {dados?.length === 0 && (
          <p className="proximas-vazio">
            {usuario
              ? 'Nenhuma sessão marcada. Cadastre uma com data futura para ela aparecer aqui.'
              : 'Nenhuma sessão marcada por enquanto.'}
          </p>
        )}
        {dados?.length > 0 && <Lista sessoes={dados} data={diaDaSessao} />}
      </div>
      {semTier?.length > 0 && (
        <div>
          <h2>Falta a tier</h2>
          <Lista sessoes={semTier} data={dataPorExtenso} />
        </div>
      )}
    </section>
  )
}
