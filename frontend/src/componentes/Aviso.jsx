/** Mensagem de erro, com botão para tentar de novo quando faz sentido. */
export default function Aviso({ erro, tentar }) {
  if (!erro) return null
  return (
    <div className="aviso" role="alert">
      <p>{erro.message}</p>
      {tentar && (
        <button type="button" className="link" onClick={tentar}>
          Tentar de novo
        </button>
      )}
    </div>
  )
}
