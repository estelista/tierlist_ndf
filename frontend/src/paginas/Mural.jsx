import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import Aviso from '../componentes/Aviso.jsx'
import DetalheSessao from '../componentes/DetalheSessao.jsx'
import Proximas from '../componentes/Proximas.jsx'
import Menu from '../componentes/Menu.jsx'
import TierList from '../componentes/TierList.jsx'
import { NOME_DA_LISTA, NOME_DO_SITE, contarTitulos } from '../textos.js'
import { useDados } from '../useDados.js'
import NaoEncontrado from './NaoEncontrado.jsx'

export default function Mural() {
  const { numero } = useParams()
  const [parametros] = useSearchParams()
  const [versao, setVersao] = useState(0)
  const { dados: abas, erro: erroAbas, recarregar: recarregarAbas } = useDados('/sessoes/anos/')

  const aba = abas?.anos.find((item) =>
    numero ? String(item.ano_do_grupo) === numero : item.ano === abas.ano_atual,
  )
  const { dados: lista, erro, recarregar } = useDados(
    aba ? `/sessoes/tier-lists/?ano=${aba.ano}` : null,
  )

  if (abas && !aba) return <NaoEncontrado texto="Este ano do grupo não existe." />

  const tabela = lista?.[0]
  const total = tabela && Object.values(tabela.tiers).reduce((soma, tier) => soma + tier.length, 0)
  const sessaoAberta = parametros.get('sessao')

  function atualizar() {
    recarregar()
    setVersao((v) => v + 1)
  }

  return (
    <div className="mural">
      <title>{aba ? `${aba.nome} | ${NOME_DO_SITE}` : NOME_DO_SITE}</title>
      <div className="topo">
        {/* faixa com as bordas furadas de um filme */}
        <div className="pelicula">
          <div className="largura topo-linha">
            <div className="topo-titulo">
              <h1>
                {NOME_DA_LISTA}
                {aba && (
                  <>
                    <span className="so-leitor">, </span>
                    <span className="topo-ano">{aba.nome}</span>
                  </>
                )}
              </h1>
              {aba && (
                <p>
                  {aba.ano}
                  {total > 0 && `, ${contarTitulos(total)}`}
                  {total === 0 && ', nenhum título avaliado ainda'}
                </p>
              )}
              {erroAbas && !abas && <Aviso erro={erroAbas} tentar={recarregarAbas} />}
              {erro && !lista && <Aviso erro={erro} tentar={recarregar} />}
            </div>
            <Proximas key={versao} />
          </div>
        </div>

        <div className="largura abas-linha">
          <nav className="abas" aria-label="Anos do grupo">
            {abas?.anos.map((item) => (
              <Link
                key={item.ano}
                to={item.ano === abas.ano_atual ? '/' : `/ano/${item.ano_do_grupo}`}
                className="aba"
                aria-current={item === aba ? 'page' : undefined}
              >
                {item.nome}
              </Link>
            ))}
          </nav>
          <Menu />
        </div>
      </div>

      <div aria-busy={Boolean(aba) && !tabela}>
        <TierList tiers={tabela?.tiers} />
      </div>

      {sessaoAberta && <DetalheSessao key={sessaoAberta} id={sessaoAberta} aoMudar={atualizar} />}
    </div>
  )
}
