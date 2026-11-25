import { useState } from 'react'
import Campo from './Campo.jsx'

/** Campo de senha com opção de mostrar o que foi digitado. */
export default function CampoSenha({ rotulo = 'Senha', erro, ajuda, ...props }) {
  const [visivel, setVisivel] = useState(false)
  return (
    <div className="campo-senha">
      <Campo rotulo={rotulo} erro={erro} ajuda={ajuda}>
        {(ligacoes) => <input {...ligacoes} {...props} type={visivel ? 'text' : 'password'} required />}
      </Campo>
      <label className="opcao">
        <input type="checkbox" checked={visivel} onChange={(e) => setVisivel(e.target.checked)} />
        Mostrar senha
      </label>
    </div>
  )
}
