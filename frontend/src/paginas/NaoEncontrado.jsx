import { Link } from 'react-router'
import { NOME_DO_SITE } from '../textos.js'

export default function NaoEncontrado({ texto = 'Esta página não existe.' }) {
  return (
    <div className="pagina">
      <title>{`Página não encontrada | ${NOME_DO_SITE}`}</title>
      <h1>{texto}</h1>
      <p>
        <Link to="/">Voltar ao mural</Link>
      </p>
    </div>
  )
}
