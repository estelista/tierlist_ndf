import { useState } from 'react'

/** Adesivo do amigo, sem corte. Quem ainda não tem um (ou tem um quebrado) aparece com a inicial. */
export default function Icone({ amigo, descrever = false }) {
  const [quebrado, setQuebrado] = useState(null)
  const { apelido, icone_url: url } = amigo
  const acessivel = descrever ? { role: 'img', 'aria-label': apelido } : { 'aria-hidden': true }

  const temDesenho = url && quebrado !== url

  return (
    <span className={temDesenho ? 'icone' : 'icone icone-inicial'} title={apelido} {...acessivel}>
      {temDesenho ? (
        <img src={url} alt="" onError={() => setQuebrado(url)} />
      ) : (
        apelido[0]?.toUpperCase()
      )}
    </span>
  )
}
