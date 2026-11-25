import { CREDITO_TMDB } from '../textos.js'

export default function Rodape() {
  return (
    <footer className="rodape">
      <div className="largura">
        <p>Dados e imagens dos títulos: TMDB.</p>
        <p lang="en">{CREDITO_TMDB}</p>
      </div>
    </footer>
  )
}
