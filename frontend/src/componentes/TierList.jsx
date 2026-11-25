import { TIERS, contarTitulos } from '../textos.js'
import CartaoSessao from './CartaoSessao.jsx'
import LetraTier from './LetraTier.jsx'

/** As cinco faixas de um ano, da S à VTNC. Sem `tiers` (carregando), mostra as faixas vazias. */
export default function TierList({ tiers }) {
  return TIERS.map((tier) => {
    const sessoes = tiers?.[tier] ?? []
    return (
      <section
        key={tier}
        className="faixa"
        data-tier={tier}
        aria-label={tiers ? `Tier ${tier}: ${contarTitulos(sessoes.length)}` : `Tier ${tier}`}
      >
        <div className="largura faixa-linha">
          <h2 className="faixa-letra">
            <span className="letra">
              <LetraTier tier={tier} />
            </span>
          </h2>
          <ul className="capas">
            {sessoes.map((sessao) => (
              <CartaoSessao key={sessao.id} sessao={sessao} />
            ))}
          </ul>
        </div>
      </section>
    )
  })
}
