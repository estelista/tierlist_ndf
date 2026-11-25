import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router'
import Cabecalho from './componentes/Cabecalho.jsx'
import Rodape from './componentes/Rodape.jsx'
import Cadastro from './paginas/Cadastro.jsx'
import Contas from './paginas/Contas.jsx'
import Entrar from './paginas/Entrar.jsx'
import FormSessao from './paginas/FormSessao.jsx'
import Mural from './paginas/Mural.jsx'
import NaoEncontrado from './paginas/NaoEncontrado.jsx'

export default function App() {
  const { pathname } = useLocation()
  const noMural = pathname === '/' || pathname.startsWith('/ano/')

  // Ao sair do mural, começa do topo (trocar de ano não mexe na rolagem).
  useEffect(() => {
    if (!noMural) window.scrollTo(0, 0)
  }, [pathname, noMural])

  return (
    <>
      <Cabecalho />
      <main>
        <Routes>
          <Route path="/" element={<Mural />} />
          <Route path="/ano/:numero" element={<Mural />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/cadastro" element={<Cadastro />} />
          <Route path="/nova-sessao" element={<FormSessao key="nova" />} />
          <Route path="/sessoes/:id/editar" element={<FormSessao key="editar" />} />
          <Route path="/contas" element={<Contas />} />
          <Route path="*" element={<NaoEncontrado />} />
        </Routes>
      </main>
      <Rodape />
    </>
  )
}
