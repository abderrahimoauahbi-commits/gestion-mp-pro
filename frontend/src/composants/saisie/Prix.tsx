/**
 * Un prix unitaire saisi dans sa devise et son unité (au kilo, ou au mètre pour un cuir, des
 * franges, un ruban) : jusqu'à quatre décimales (0,0011 USD / ml ne devient pas 0,00). Un prix au
 * mètre dit son équivalent au kilo (`densite` en kg/ml), celui de tous les calculs.
 */
import { prixUnite } from '../../lib/format'
import { Nombre } from './Nombre'
import styles from './controle.module.css'

/** Le prix au kilo d'un prix au mètre (kg/ml) ; `null` sans densité. */
export function prixAuKg(prixMl: number | null, densite: number | null | undefined): number | null {
  if (prixMl == null || !densite || densite <= 0) return null
  return prixMl / densite
}

export interface PrixProps {
  valeur: number | null
  onChange: (valeur: number | null) => void
  devise: string
  unite: 'kg' | 'ml'
  densite?: number | null
  libelle?: string
  desactive?: boolean
}

export function Prix({ valeur, onChange, devise, unite, densite, libelle, desactive }: PrixProps) {
  const auKg = unite === 'ml' ? prixAuKg(valeur, densite) : null
  return (
    <>
      <Nombre
        valeur={valeur}
        onChange={onChange}
        unite={`${devise} / ${unite}`}
        decimales={4}
        min={0}
        libelle={libelle}
        desactive={desactive}
      />
      {auKg != null ? <span className={styles.note}>soit {prixUnite(auKg, devise, 'kg')}</span> : null}
      {unite === 'ml' && !densite ? (
        <span className={styles.message}>
          Densité inconnue (kg / ml) : l’équivalent au kilo ne peut pas se calculer.
        </span>
      ) : null}
    </>
  )
}
