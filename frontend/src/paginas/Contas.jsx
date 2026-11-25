import { useState } from 'react'
import { api } from '../api.js'
import Aviso from '../componentes/Aviso.jsx'
import BotaoConfirmar from '../componentes/BotaoConfirmar.jsx'
import Campo from '../componentes/Campo.jsx'
import { useUsuario } from '../sessao.js'
import { NOME_DO_SITE, momento } from '../textos.js'
import { useDados } from '../useDados.js'
import NaoEncontrado from './NaoEncontrado.jsx'
import PedirLogin from './PedirLogin.jsx'

function Pedido({ pedido, aoResolver }) {
  const [icone, setIcone] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  async function resolver(acao, mensagem, corpo) {
    setErro(null)
    setEnviando(true)
    try {
      await api(`/cadastros/${pedido.id}/${acao}/`, { metodo: 'POST', corpo })
      aoResolver(mensagem)
    } catch (falha) {
      setErro(falha)
      setEnviando(false)
    }
  }

  function aprovar(evento) {
    evento.preventDefault()
    const corpo = icone.trim() ? { icone_url: icone.trim() } : {}
    resolver('aprovar', `Conta de ${pedido.apelido} aprovada.`, corpo)
  }

  return (
    <li className="pedido">
      <h2>{pedido.apelido}</h2>
      <p>Pediu a conta em {momento(pedido.criado_em)}.</p>
      {pedido.amigo_existente && (
        <p>Já aparece no mural com esse apelido: ao aprovar, a conta será ligada a esse amigo.</p>
      )}
      <form onSubmit={aprovar}>
        <Campo
          rotulo="Ícone (opcional)"
          ajuda="Endereço da imagem. Por exemplo: /icones/ana.png"
          erro={erro?.campos.icone_url}
        >
          {(ligacoes) => (
            <input
              {...ligacoes}
              maxLength="300"
              autoCapitalize="none"
              value={icone}
              onChange={(e) => setIcone(e.target.value)}
            />
          )}
        </Campo>
        {!erro?.campos.icone_url && <Aviso erro={erro} />}
        <div className="acoes">
          <button type="submit" className="botao" disabled={enviando}>
            Aprovar conta
          </button>
          <BotaoConfirmar
            pergunta="Recusar e apagar este pedido?"
            confirmar="Recusar"
            aoConfirmar={() => resolver('recusar', `Pedido de ${pedido.apelido} recusado.`)}
          >
            Recusar
          </BotaoConfirmar>
        </div>
      </form>
    </li>
  )
}

function Pedidos() {
  const { dados, erro, recarregar } = useDados('/cadastros/')
  const [mensagem, setMensagem] = useState('')
  return (
    <div className="pagina pagina-estreita">
      <title>{`Contas | ${NOME_DO_SITE}`}</title>
      <h1>Contas para aprovar</h1>
      <p role="status" className="mensagem">
        {mensagem}
      </p>
      <Aviso erro={erro} tentar={recarregar} />
      {dados?.length === 0 && (
        <p>Nenhum pedido esperando. Quando alguém criar uma conta, ela aparece aqui.</p>
      )}
      <ul className="pedidos">
        {dados?.map((pedido) => (
          <Pedido
            key={pedido.id}
            pedido={pedido}
            aoResolver={(texto) => {
              setMensagem(texto)
              recarregar()
            }}
          />
        ))}
      </ul>
    </div>
  )
}

export default function Contas() {
  const usuario = useUsuario()
  if (!usuario) return <PedirLogin titulo="Contas para aprovar" />
  if (!usuario.is_admin) return <NaoEncontrado texto="Só a administradora aprova contas." />
  return <Pedidos />
}
