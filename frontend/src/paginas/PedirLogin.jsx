import { Link, useLocation } from 'react-router'

/** No lugar de uma página que precisa de login. */
export default function PedirLogin({ titulo }) {
  const { pathname, search } = useLocation()
  return (
    <div className="pagina">
      <h1>{titulo}</h1>
      <p>Esta parte é só para os amigos do grupo.</p>
      <p>
        <Link to="/entrar" state={{ voltar: pathname + search }} className="botao">
          Entrar
        </Link>
      </p>
    </div>
  )
}
