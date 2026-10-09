/**
 * « + N non répartis » (I15, ECRANS-PRO 5.1, 5.15) : des frais saisis sans marchandise où se
 * répartir ne sont dans aucun coût ; ils se disent à part, en rouge, et chaque dossier qui en porte
 * s'ouvre d'un clic (une liste de liens, plus seulement le premier dossier).
 */
import { LienDocument } from '../../composants/documents/LienDocument'
import { montantCourt, montantPrecis } from '../../lib/format'
import styles from './Importations.module.css'

export interface DossierNonReparti {
  id: number | null
  numero: string
  montant: number
}

export function NonRepartis({ dossiers }: { dossiers: readonly DossierNonReparti[] }) {
  if (!dossiers.length) return null
  const total = dossiers.reduce((s, d) => s + d.montant, 0)
  return (
    <details
      className={styles.nonRepartis}
      onClick={(e) => e.stopPropagation()}
      title={`Frais sans marchandise, dans aucun coût : ${dossiers
        .map((d) => `${d.numero} (${montantPrecis(d.montant, 'MAD')})`)
        .join(', ')}`}
    >
      <summary>+ {montantCourt(total, 'MAD')} non répartis</summary>
      <ul aria-label="Dossiers aux frais non répartis">
        {dossiers.map((d) => (
          <li key={d.numero}>
            <LienDocument genre="dossier" id={d.id} numero={d.numero} />
            <span>{montantPrecis(d.montant, 'MAD')}</span>
          </li>
        ))}
      </ul>
    </details>
  )
}
