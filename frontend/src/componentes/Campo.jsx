import { useId } from 'react'

/** Rótulo + campo + ajuda + erro, ligados para leitores de tela. */
export default function Campo({ rotulo, erro, ajuda, children }) {
  const id = useId()
  const texto = erro || ajuda
  return (
    <div className="campo">
      <label htmlFor={id}>{rotulo}</label>
      {children({
        id,
        'aria-describedby': texto ? `${id}-d` : undefined,
        'aria-invalid': erro ? true : undefined,
      })}
      {texto && (
        <p id={`${id}-d`} className={erro ? 'campo-erro' : 'campo-ajuda'}>
          {texto}
        </p>
      )}
    </div>
  )
}
