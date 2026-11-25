import { Link, NavLink, useLocation } from 'react-router'
import { encerrarSessao, useUsuario } from '../sessao.js'
import { useDados } from '../useDados.js'
import Icone from './Icone.jsx'

/** Entrar, ou a conta e as ações de quem está logado. */
export default function Menu() {
  const usuario = useUsuario()
  const { pathname, search } = useLocation()
  // Sair da tela de contas relê o número de pedidos.
  const { dados: pendentes } = useDados(
    usuario?.is_admin && pathname !== '/contas' ? '/cadastros/' : null,
  )
  const naConta = pathname === '/entrar' || pathname === '/cadastro'

  return (
    <nav className="menu" aria-label="Menu">
      {usuario ? (
        <>
          <span className="conta">
            <Icone amigo={usuario} />
            <span className="conta-nome">{usuario.apelido}</span>
          </span>
          <button type="button" className="link" onClick={encerrarSessao}>
            Sair
          </button>
          {usuario.is_admin && (
            <NavLink to="/contas" className="link">
              Contas{pendentes?.length > 0 && ` (${pendentes.length})`}
            </NavLink>
          )}
          <NavLink to="/nova-sessao" className="botao">
            Cadastrar sessão
          </NavLink>
        </>
      ) : (
        <Link
          to="/entrar"
          state={naConta ? null : { voltar: pathname + search }}
          className="botao"
        >
          Entrar
        </Link>
      )}
    </nav>
  )
}
