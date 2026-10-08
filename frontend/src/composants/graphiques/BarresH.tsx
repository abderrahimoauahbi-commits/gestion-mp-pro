/**
 * Des barres horizontales (classements, Pareto des fournisseurs) : libellé, valeur à droite avec
 * son unité, barre proportionnelle au plus grand. Une seule unité par liste.
 */
import { nombre } from '../../lib/format'
import { couleurDeSerie } from '../../lib/teintes'
import styles from './BarresH.module.css'

export interface LigneBarresH {
  libelle: string
  valeur: number
  detail?: string
  couleur?: string
}

export function BarresH({
  lignes,
  libelle,
  unite,
  format = (v) => nombre(v, 0, 1),
}: {
  lignes: readonly LigneBarresH[]
  libelle: string
  unite?: string
  format?: (v: number) => string
}) {
  const max = Math.max(1e-9, ...lignes.map((l) => Math.abs(l.valeur)))
  if (!lignes.length) return <div className={styles.vide}>Pas de données à montrer.</div>
  return (
    <ul className={styles.barresH} aria-label={libelle}>
      {lignes.map((l, i) => (
        <li key={`${l.libelle}-${i}`} className={styles.ligne}>
          <span className={styles.libelle}>{l.libelle}</span>
          <span className={styles.valeur}>
            {format(l.valeur)}
            {unite ? `\u00a0${unite}` : ''}
            {l.detail ? <small className={styles.detail}> · {l.detail}</small> : null}
          </span>
          <span className={styles.piste} aria-hidden="true">
            <span
              className={styles.barre}
              style={{
                width: `${(Math.abs(l.valeur) / max) * 100}%`,
                background: l.couleur ?? couleurDeSerie(0),
              }}
            />
          </span>
        </li>
      ))}
    </ul>
  )
}
