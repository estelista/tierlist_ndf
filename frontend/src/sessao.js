// Login guardado no navegador: { access, refresh, usuario }.
import { useSyncExternalStore } from 'react'

const CHAVE = 'noitedofilme.login'
const ouvintes = new Set()
let atual = carregar()

function carregar() {
  try {
    const dados = JSON.parse(localStorage.getItem(CHAVE))
    return dados?.refresh && dados?.usuario ? dados : null
  } catch {
    return null
  }
}

function guardar(dados) {
  // Mantém o mesmo objeto de usuário se nada mudou, para não redesenhar o site à toa.
  if (atual && dados && JSON.stringify(atual.usuario) === JSON.stringify(dados.usuario)) {
    dados = { ...dados, usuario: atual.usuario }
  }
  atual = dados
  try {
    if (dados) localStorage.setItem(CHAVE, JSON.stringify(dados))
    else localStorage.removeItem(CHAVE)
  } catch {
    // Navegador sem armazenamento: o login vale até fechar a aba.
  }
  ouvintes.forEach((avisar) => avisar())
}

export const lerSessao = () => atual
export const salvarSessao = ({ access, refresh, usuario }) => guardar({ access, refresh, usuario })
export const encerrarSessao = () => guardar(null)

// Entrar ou sair em outra aba vale para esta também.
window.addEventListener('storage', (evento) => {
  if (evento.key === CHAVE || evento.key === null) {
    atual = carregar()
    ouvintes.forEach((avisar) => avisar())
  }
})

function assinar(avisar) {
  ouvintes.add(avisar)
  return () => ouvintes.delete(avisar)
}

/** Usuário logado (apelido, icone_url, amigo_id, is_admin), ou null. */
export function useUsuario() {
  return useSyncExternalStore(assinar, () => atual?.usuario ?? null)
}
