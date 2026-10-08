/**
 * Un montant, devise toujours dite : entier dans les tableaux et indicateurs (le centime en
 * infobulle), au centime dans les documents (`precis`), « 17,4 M MAD » dans un indicateur
 * (`court`). Plusieurs devises (`parDevise`) ne s'additionnent jamais : « 61 888 USD · 53 132 EUR ».
 */
import { montant, montantCourt, montantPrecis, montants } from '../../lib/format'

export type MontantProps =
  | { valeur: number | null | undefined; devise: string; precis?: boolean; court?: boolean }
  | { parDevise: Record<string, number> | null | undefined; precis?: boolean }

export function Montant(props: MontantProps) {
  if ('parDevise' in props) {
    return (
      <span className="nombre" title={montants(props.parDevise, true)}>
        {montants(props.parDevise, props.precis)}
      </span>
    )
  }
  const { valeur, devise, precis, court } = props
  const texte = precis
    ? montantPrecis(valeur, devise)
    : court
      ? montantCourt(valeur, devise)
      : montant(valeur, devise)
  const exact = montantPrecis(valeur, devise)
  return (
    <span className="nombre" title={exact === texte ? undefined : exact}>
      {texte}
    </span>
  )
}
