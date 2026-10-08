/**
 * Un indicateur (ECRANS-PRO § 3) : titre, valeur avec son unité, et **toujours sa formule**
 * (bulle « ? », AMELIORATIONS 13) — le type l'exige, et une formule vide est signalée. Le ton
 * pose un filet de couleur en haut ; le texte (`detail`) dit ce que la couleur montre. Avec
 * `lien`, l'indicateur ouvre l'écran qui le détaille (P1-27). La valeur exacte d'un montant
 * abrégé (« 17,4 M MAD ») va en infobulle (`exact`).
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import type { Ton } from '../../lib/statuts'
import { classes } from '../mise-en-page/classes'
import { Formule } from './Formule'
import styles from './Kpi.module.css'

export interface KpiProps {
  titre: string
  valeur: ReactNode
  unite?: string
  /** La formule du calcul (`aide.json`, `formule.<cle>`) : obligatoire. */
  formule: string
  detail?: ReactNode
  ton?: Ton
  lien?: string
  exact?: string
  grand?: boolean
}

export function Kpi({ titre, valeur, unite, formule, detail, ton, lien, exact, grand }: KpiProps) {
  if (!(formule ?? '').trim())
    console.error(`Indicateur « ${titre} » sans formule : elle est obligatoire (aide.json).`)
  const corps = (
    <>
      <div className={styles.titre}>
        <span>{titre}</span>
        <Formule texte={formule} de={titre} />
      </div>
      <div className={styles.valeur} title={exact}>
        {valeur}
        {unite ? <span className={styles.unite}> {unite}</span> : null}
      </div>
      {detail != null ? <div className={styles.detail}>{detail}</div> : null}
    </>
  )
  const nom = classes(styles.kpi, ton && styles[ton], grand && styles.grand, lien && styles.lien)
  return lien ? (
    <Link to={lien} className={nom} data-ton={ton}>
      {corps}
    </Link>
  ) : (
    <div className={nom} data-ton={ton}>
      {corps}
    </div>
  )
}
