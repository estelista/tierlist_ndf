/** A tier como aparece na tela: a letra ou, na VTNC, o dedo do meio (leitores de tela leem o nome). */
export default function LetraTier({ tier }) {
  if (tier !== 'VTNC') return tier
  return (
    <>
      <span className="so-leitor">{tier}</span>
      <svg className="dedo" viewBox="-2 -6 114 132" aria-hidden="true">
        <title>{tier}</title>
        <path
          className="dedo-forma"
          d="M36 114C31 100 14 93 11 79C9 68 17 62 24 65V56C24 44 42 44 42 55V20C42 4 63 4 63 20V55C63 44 81 44 81 57C81 49 98 49 98 62V84C98 98 88 103 85 114Z"
        />
        <path className="dedo-linha" d="M42 56V70M63 56V70M81 58V70M24 66C35 69 43 76 45 88" />
      </svg>
    </>
  )
}
