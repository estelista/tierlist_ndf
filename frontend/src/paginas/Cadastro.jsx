import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { api } from '../api.js'
import Aviso from '../componentes/Aviso.jsx'
import Campo from '../componentes/Campo.jsx'
import CampoSenha from '../componentes/CampoSenha.jsx'
import { NOME_DO_SITE } from '../textos.js'

export default function Cadastro() {
  const { state } = useLocation()
  const [dados, setDados] = useState({ apelido: '', senha: '', codigo_convite: '' })
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [resposta, setResposta] = useState('')

  const mudar = (campo) => (evento) => setDados({ ...dados, [campo]: evento.target.value })
  const campos = erro?.campos ?? {}
  const semCampo = erro && !campos.apelido && !campos.senha && !campos.codigo_convite

  async function enviar(evento) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      const { detail } = await api('/auth/registro/', { metodo: 'POST', corpo: dados, publica: true })
      setResposta(detail)
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  if (resposta) {
    return (
      <div className="pagina pagina-estreita">
        <title>{`Criar conta | ${NOME_DO_SITE}`}</title>
        <h1>Conta pedida</h1>
        <p role="status">{resposta}</p>
        <p>
          <Link to="/">Voltar ao mural</Link>
        </p>
      </div>
    )
  }

  return (
    <div className="pagina pagina-estreita">
      <title>{`Criar conta | ${NOME_DO_SITE}`}</title>
      <h1>Criar conta</h1>
      <form onSubmit={enviar}>
        <Campo
          rotulo="Apelido"
          erro={campos.apelido}
          ajuda="Se você já aparece no mural, use o mesmo apelido."
        >
          {(ligacoes) => (
            <input
              {...ligacoes}
              autoComplete="username"
              minLength="2"
              maxLength="50"
              required
              value={dados.apelido}
              onChange={mudar('apelido')}
            />
          )}
        </Campo>
        <CampoSenha
          autoComplete="new-password"
          ajuda="Pelo menos 8 caracteres, e não só números."
          erro={campos.senha}
          value={dados.senha}
          onChange={mudar('senha')}
        />
        <Campo
          rotulo="Código de convite"
          erro={campos.codigo_convite}
          ajuda="Peça o código para a administradora do grupo."
        >
          {(ligacoes) => (
            <input
              {...ligacoes}
              autoComplete="off"
              autoCapitalize="none"
              required
              value={dados.codigo_convite}
              onChange={mudar('codigo_convite')}
            />
          )}
        </Campo>
        {semCampo && <Aviso erro={erro} />}
        <button type="submit" className="botao" disabled={enviando}>
          Criar conta
        </button>
      </form>
      <p>
        Já tem conta?{' '}
        <Link to="/entrar" state={state}>
          Entrar
        </Link>
      </p>
    </div>
  )
}
