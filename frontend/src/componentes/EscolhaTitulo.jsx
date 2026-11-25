import { useEffect, useId, useState } from 'react'
import { api } from '../api.js'
import { nomeDoTipo } from '../textos.js'
import Capa from './Capa.jsx'

/** Busca no TMDB. Se ele estiver fora do ar, procura entre os títulos que já estão no site. */
async function procurar(texto, ano, signal) {
  const consulta = new URLSearchParams({ q: texto })
  if (ano) consulta.set('ano', ano)
  try {
    const resultados = await api(`/tmdb/buscar/?${consulta}`, { signal })
    return { resultados, aviso: '' }
  } catch (erro) {
    if (erro.status !== 502) throw erro
    const busca = new URLSearchParams({ search: texto })
    if (ano) busca.set('ano_lancamento', ano)
    const { results } = await api(`/filmes/?${busca}`, { signal })
    return {
      resultados: results,
      aviso: `${erro.message} Estes são os títulos que já estão no site.`,
    }
  }
}

function Resumo({ titulo }) {
  return (
    <span className="titulo-texto">
      <strong>{titulo.titulo}</strong>
      <span>
        {nomeDoTipo(titulo.tipo)}
        {titulo.ano_lancamento && ` de ${titulo.ano_lancamento}`}
      </span>
    </span>
  )
}

export default function EscolhaTitulo({ valor, aoEscolher, erro }) {
  const id = useId()
  const [texto, setTexto] = useState('')
  const [ano, setAno] = useState('')
  const [estado, setEstado] = useState(null) // { resultados, aviso } ou { erro }
  const limpo = texto.trim()

  useEffect(() => {
    if (limpo.length < 2 || valor) return undefined
    const controle = new AbortController()
    // Espera a pessoa parar de digitar: a API aceita 60 buscas por minuto.
    const espera = setTimeout(() => {
      procurar(limpo, /^\d{4}$/.test(ano) ? ano : '', controle.signal)
        .then((achados) => !controle.signal.aborted && setEstado(achados))
        .catch((falha) => !controle.signal.aborted && setEstado({ erro: falha.message }))
    }, 500)
    return () => {
      clearTimeout(espera)
      controle.abort()
    }
  }, [limpo, ano, valor])

  if (valor) {
    return (
      <div className="campo">
        <p className="campo-nome">Título</p>
        <div className="titulo-escolhido">
          <Capa titulo={valor.titulo} url={valor.poster_url} alt="" />
          <div>
            <Resumo titulo={valor} />
            <button type="button" className="link" onClick={() => aoEscolher(null)}>
              Trocar título
            </button>
          </div>
        </div>
        {erro && <p className="campo-erro">{erro}</p>}
      </div>
    )
  }

  const visivel = limpo.length >= 2 ? estado : null

  return (
    <div className="campo">
      <div className="busca">
        <div className="campo">
          <label htmlFor={`${id}-t`}>Título</label>
          <input
            id={`${id}-t`}
            type="search"
            autoComplete="off"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            aria-invalid={erro ? true : undefined}
            aria-describedby={`${id}-d`}
          />
        </div>
        <div className="campo">
          <label htmlFor={`${id}-a`}>Ano (opcional)</label>
          <input
            id={`${id}-a`}
            inputMode="numeric"
            maxLength="4"
            value={ano}
            onChange={(e) => setAno(e.target.value.replace(/\D/g, ''))}
          />
        </div>
      </div>
      <p id={`${id}-d`} className={erro ? 'campo-erro' : 'campo-ajuda'}>
        {erro || 'Busque um filme ou uma série e escolha na lista.'}
      </p>
      <div aria-live="polite">
        {visivel?.erro && <p className="campo-erro">{visivel.erro}</p>}
        {visivel?.aviso && <p className="campo-ajuda">{visivel.aviso}</p>}
        {visivel?.resultados?.length === 0 && <p>Nada encontrado. Confira o nome e o ano.</p>}
      </div>
      {visivel?.resultados?.length > 0 && (
        <ul className="resultados">
          {visivel.resultados.map((titulo) => (
            <li key={`${titulo.tipo}-${titulo.tmdb_id ?? titulo.id}`}>
              <button type="button" onClick={() => aoEscolher(titulo)}>
                <Capa titulo={titulo.titulo} url={titulo.poster_url} alt="" />
                <Resumo titulo={titulo} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
