import { useCallback, useEffect, useState } from 'react'
import { api, apiTudo, cache } from './api.js'
import { useUsuario } from './sessao.js'

/**
 * Lê um endereço da API. `caminho` vazio não busca nada.
 * Com `todas`, junta as páginas e devolve a lista inteira.
 */
export function useDados(caminho, { todas = false } = {}) {
  const usuario = useUsuario()
  // O que a API devolve depende de quem está logado (pode_editar, comentários).
  const chave = caminho ? `${usuario?.id ?? 'visitante'} ${caminho}` : null
  const [versao, setVersao] = useState(0)
  const [estado, setEstado] = useState({ chave: null, dados: null, erro: null })

  useEffect(() => {
    if (!chave) return undefined
    const controle = new AbortController()
    const buscar = todas ? apiTudo : api
    buscar(caminho, { signal: controle.signal })
      .then((dados) => {
        if (controle.signal.aborted) return
        cache.set(chave, dados)
        setEstado({ chave, dados, erro: null })
      })
      .catch((erro) => {
        if (controle.signal.aborted) return
        setEstado({ chave, dados: cache.get(chave) ?? null, erro })
      })
    return () => controle.abort()
  }, [chave, caminho, todas, versao])

  const recarregar = useCallback(() => setVersao((v) => v + 1), [])
  const atual = estado.chave === chave
  return {
    dados: (atual ? estado.dados : cache.get(chave)) ?? null,
    erro: atual ? estado.erro : null,
    recarregar,
  }
}
