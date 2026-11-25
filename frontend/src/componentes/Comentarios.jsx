import { useState } from 'react'
import { Link, useLocation } from 'react-router'
import { api, urlDaFoto } from '../api.js'
import { useUsuario } from '../sessao.js'
import { momento } from '../textos.js'
import { useDados } from '../useDados.js'
import Aviso from './Aviso.jsx'
import BotaoConfirmar from './BotaoConfirmar.jsx'
import FormComentario from './FormComentario.jsx'
import Icone from './Icone.jsx'

function Comentario({ comentario, aoMudar }) {
  const usuario = useUsuario()
  const [editando, setEditando] = useState(false)
  const [erro, setErro] = useState(null)
  const meu = usuario?.amigo_id === comentario.autor
  const autor = { apelido: comentario.autor_apelido, icone_url: comentario.autor_icone_url }

  async function apagar(caminho) {
    setErro(null)
    try {
      await api(caminho, { metodo: 'DELETE' })
      aoMudar()
    } catch (falha) {
      setErro(falha)
    }
  }

  return (
    <li className="comentario">
      <Icone amigo={autor} />
      <div>
        <p className="comentario-autor">
          <strong>{autor.apelido}</strong>{' '}
          <time dateTime={comentario.criado_em}>{momento(comentario.criado_em)}</time>
        </p>
        {!editando && <p className="comentario-texto">{comentario.texto}</p>}
        {comentario.fotos.length > 0 && (
          <ul className="fotos">
            {comentario.fotos.map((foto, indice) => (
              <li key={foto.id}>
                <a href={urlDaFoto(foto.imagem)} target="_blank" rel="noreferrer">
                  <img
                    src={urlDaFoto(foto.imagem)}
                    alt={`Foto ${indice + 1} de ${autor.apelido}`}
                    loading="lazy"
                  />
                </a>
                {editando && (
                  <BotaoConfirmar
                    pergunta="Apagar a foto?"
                    confirmar="Apagar"
                    aoConfirmar={() => apagar(`/fotos/${foto.id}/`)}
                  >
                    Apagar foto
                  </BotaoConfirmar>
                )}
              </li>
            ))}
          </ul>
        )}
        {editando && (
          <FormComentario
            sessao={comentario.sessao}
            comentario={comentario}
            aoSalvar={() => {
              setEditando(false)
              aoMudar()
            }}
            aoCancelar={() => setEditando(false)}
          />
        )}
        {!editando && comentario.pode_editar && (
          <div className="acoes">
            {meu && (
              <button type="button" className="link" onClick={() => setEditando(true)}>
                Alterar
              </button>
            )}
            <BotaoConfirmar
              pergunta="Apagar o comentário?"
              confirmar="Apagar"
              aoConfirmar={() => apagar(`/comentarios/${comentario.id}/`)}
            >
              Apagar
            </BotaoConfirmar>
          </div>
        )}
        <Aviso erro={erro} />
      </div>
    </li>
  )
}

function ComentariosDosAmigos({ sessao, usuario }) {
  const { dados, erro, recarregar } = useDados(`/comentarios/?sessao=${sessao.id}`, { todas: true })
  return (
    <>
      <Aviso erro={erro} tentar={recarregar} />
      {dados?.length === 0 && <p className="nota">Ninguém comentou ainda.</p>}
      {dados?.length > 0 && (
        <ul className="comentarios">
          {dados.map((comentario) => (
            <Comentario key={comentario.id} comentario={comentario} aoMudar={recarregar} />
          ))}
        </ul>
      )}
      {usuario.amigo_id === null ? (
        <p className="nota">
          Para comentar, sua conta precisa estar ligada a um amigo do grupo. Isso é feito no painel
          do Django (/admin/).
        </p>
      ) : (
        <FormComentario sessao={sessao.id} aoSalvar={recarregar} />
      )}
    </>
  )
}

export default function Comentarios({ sessao }) {
  const usuario = useUsuario()
  const { pathname, search } = useLocation()
  return (
    <section>
      <h3>Comentários</h3>
      {usuario ? (
        <ComentariosDosAmigos sessao={sessao} usuario={usuario} />
      ) : (
        <p className="nota">
          Só os amigos veem os comentários e as fotos.{' '}
          <Link to="/entrar" state={{ voltar: pathname + search }}>
            Entrar
          </Link>
        </p>
      )}
    </section>
  )
}
