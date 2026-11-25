import { useState } from 'react'
import { Link, Navigate, useLocation } from 'react-router'
import { entrar } from '../api.js'
import Aviso from '../componentes/Aviso.jsx'
import Campo from '../componentes/Campo.jsx'
import CampoSenha from '../componentes/CampoSenha.jsx'
import { useUsuario } from '../sessao.js'
import { NOME_DO_SITE } from '../textos.js'

export default function Entrar() {
  const usuario = useUsuario()
  const { state } = useLocation()
  const [apelido, setApelido] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  if (usuario) return <Navigate to={state?.voltar ?? '/'} replace />

  async function enviar(evento) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await entrar(apelido.trim(), senha)
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="pagina pagina-estreita">
      <title>{`Entrar | ${NOME_DO_SITE}`}</title>
      <h1>Entrar</h1>
      <form onSubmit={enviar}>
        <Campo rotulo="Apelido">
          {(ligacoes) => (
            <input
              {...ligacoes}
              autoComplete="username"
              autoCapitalize="none"
              required
              value={apelido}
              onChange={(e) => setApelido(e.target.value)}
            />
          )}
        </Campo>
        <CampoSenha
          autoComplete="current-password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        <Aviso erro={erro} />
        <button type="submit" className="botao" disabled={enviando}>
          Entrar
        </button>
      </form>
      <p>
        Ainda não tem conta?{' '}
        <Link to="/cadastro" state={state}>
          Criar conta
        </Link>
      </p>
    </div>
  )
}
