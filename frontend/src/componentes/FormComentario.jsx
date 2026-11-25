import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { useUsuario } from '../sessao.js'
import Aviso from './Aviso.jsx'
import Campo from './Campo.jsx'

const MAX_FOTOS = 4
const MAX_MB = 5
const TAMANHO_MAXIMO = MAX_MB * 1024 * 1024
// Sem HEIC: com esta lista, o iPhone converte a foto para JPEG sozinho.
const FORMATOS = 'image/jpeg,image/png,image/webp,image/gif'

// Texto ainda não enviado, por pessoa e sessão: fechar a janela sem querer não apaga nada.
const rascunhos = new Map()

/** Escrever um comentário novo ou, com `comentario`, alterar um que já existe. */
export default function FormComentario({ sessao, comentario, aoSalvar, aoCancelar }) {
  const chave = `${useUsuario()?.id}-${sessao}`
  const [texto, setTexto] = useState(comentario?.texto ?? rascunhos.get(chave) ?? '')
  const [fotos, setFotos] = useState([]) // [{ arquivo, previa }]
  const [erroFotos, setErroFotos] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const campoFotos = useRef(null)
  const previas = useRef(new Set())

  // Libera as prévias da memória ao fechar o formulário.
  useEffect(() => {
    const urls = previas.current
    return () => urls.forEach((url) => URL.revokeObjectURL(url))
  }, [])

  function escrever(valor) {
    setTexto(valor)
    if (!comentario) rascunhos.set(chave, valor)
  }

  function adicionarFotos(evento) {
    const escolhidas = [...evento.target.files]
    evento.target.value = '' // permite escolher o mesmo arquivo de novo
    const cabem = MAX_FOTOS - (comentario?.fotos.length ?? 0) - fotos.length
    const grandes = escolhidas.filter((foto) => foto.size > TAMANHO_MAXIMO)
    const boas = escolhidas.filter((foto) => foto.size <= TAMANHO_MAXIMO)
    if (grandes.length > 0) {
      setErroFotos(`Cada foto pode ter no máximo ${MAX_MB} MB: ${grandes.map((f) => f.name).join(', ')}.`)
    } else if (boas.length > cabem) {
      setErroFotos(`São no máximo ${MAX_FOTOS} fotos por comentário.`)
    } else {
      setErroFotos('')
    }
    const novas = boas.slice(0, Math.max(cabem, 0)).map((arquivo) => {
      const previa = URL.createObjectURL(arquivo)
      previas.current.add(previa)
      return { arquivo, previa }
    })
    setFotos([...fotos, ...novas])
  }

  async function enviar(evento) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    const corpo = new FormData()
    corpo.append('texto', texto)
    if (!comentario) corpo.append('sessao', sessao)
    fotos.forEach(({ arquivo }) => corpo.append('imagens', arquivo))
    try {
      if (comentario) {
        await api(`/comentarios/${comentario.id}/`, { metodo: 'PATCH', corpo })
      } else {
        await api('/comentarios/', { metodo: 'POST', corpo })
        escrever('')
      }
      setFotos([])
      setErroFotos('')
      aoSalvar()
    } catch (falha) {
      setErro(falha)
    } finally {
      setEnviando(false)
    }
  }

  const { texto: erroTexto, imagens: erroImagens, sessao: erroSessao } = erro?.campos ?? {}
  const geral = erro && !erroTexto && !erroImagens ? { message: erroSessao ?? erro.message } : null

  return (
    <form className="form-comentario" onSubmit={enviar}>
      <Campo rotulo={comentario ? 'Seu comentário' : 'Comentar'} erro={erroTexto}>
        {(ligacoes) => (
          <textarea
            {...ligacoes}
            rows="3"
            minLength="2"
            maxLength="1000"
            required
            value={texto}
            onChange={(e) => escrever(e.target.value)}
          />
        )}
      </Campo>
      {fotos.length > 0 && (
        <ul className="fotos">
          {fotos.map(({ arquivo, previa }) => (
            <li key={previa}>
              <img src={previa} alt={arquivo.name} />
              <button
                type="button"
                className="link"
                onClick={() => {
                  setErroFotos('')
                  setFotos(fotos.filter((foto) => foto.previa !== previa))
                }}
              >
                Tirar
              </button>
            </li>
          ))}
        </ul>
      )}
      {(erroFotos || erroImagens) && (
        <p className="campo-erro" role="alert">
          {erroFotos || erroImagens}
        </p>
      )}
      <Aviso erro={geral} />
      <input
        ref={campoFotos}
        type="file"
        accept={FORMATOS}
        multiple
        hidden
        aria-label="Fotos do comentário"
        onChange={adicionarFotos}
      />
      <div className="acoes">
        <button type="submit" className="botao" disabled={enviando}>
          {comentario ? 'Salvar comentário' : 'Comentar'}
        </button>
        <button type="button" className="link" onClick={() => campoFotos.current.click()}>
          Adicionar fotos
        </button>
        {aoCancelar && (
          <button type="button" className="link" onClick={aoCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
