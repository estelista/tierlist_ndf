import { Link, useLocation } from 'react-router'
import { NOME_DO_SITE } from '../textos.js'
import Menu from './Menu.jsx'

/** Barra das outras páginas. No mural ela some: o menu fica na linha das abas dos anos. */
export default function Cabecalho() {
  const { pathname } = useLocation()
  if (pathname === '/' || pathname.startsWith('/ano/')) return null

  return (
    <header className="cabecalho">
      <div className="largura cabecalho-linha">
        <Link to="/" className="marca">
          {NOME_DO_SITE}
        </Link>
        <Menu />
      </div>
    </header>
  )
}
