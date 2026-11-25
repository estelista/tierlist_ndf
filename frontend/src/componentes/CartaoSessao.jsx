import { Link, useLocation } from 'react-router'
import Capa from './Capa.jsx'
import Icone from './Icone.jsx'

/** Link que abre os detalhes de uma sessão por cima da página atual. */
export function LinkSessao({ sessao, children, ...props }) {
  const { pathname } = useLocation()
  return (
    <Link
      to={{ pathname, search: `?sessao=${sessao.id}` }}
      state={{ sessao, abertaNoSite: true }}
      {...props}
    >
      {children}
    </Link>
  )
}

/** Quem indicou a sessão. */
export function Indicadores({ sessao }) {
  return (
    <span className="indicadores">
      {sessao.sugerido_por_detalhe.map((amigo) => (
        <Icone key={amigo.id} amigo={amigo} descrever />
      ))}
    </span>
  )
}

/** Capa com os adesivos de quem indicou colados no canto de baixo, à direita. */
export default function CartaoSessao({ sessao }) {
  return (
    <li className="cartao">
      <LinkSessao sessao={sessao} className="cartao-capa" title={sessao.filme_titulo}>
        <Capa titulo={sessao.filme_titulo} url={sessao.filme_poster_url} />
        <Indicadores sessao={sessao} />
      </LinkSessao>
    </li>
  )
}
