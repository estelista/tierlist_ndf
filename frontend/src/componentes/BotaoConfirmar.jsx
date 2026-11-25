import { useState } from 'react'

/** Botão que pede confirmação no próprio lugar antes de agir (apagar, recusar). */
export default function BotaoConfirmar({ children, pergunta, confirmar, aoConfirmar }) {
  const [aberto, setAberto] = useState(false)
  const [ocupado, setOcupado] = useState(false)

  if (!aberto) {
    return (
      <button type="button" className="link" onClick={() => setAberto(true)}>
        {children}
      </button>
    )
  }

  async function agir() {
    setOcupado(true)
    try {
      await aoConfirmar()
    } finally {
      setOcupado(false)
      setAberto(false)
    }
  }

  return (
    <span className="confirmacao" role="group" aria-label={pergunta}>
      <span>{pergunta}</span>
      <button type="button" className="link perigo" onClick={agir} disabled={ocupado} autoFocus>
        {confirmar}
      </button>
      <button type="button" className="link" onClick={() => setAberto(false)} disabled={ocupado}>
        Cancelar
      </button>
    </span>
  )
}
