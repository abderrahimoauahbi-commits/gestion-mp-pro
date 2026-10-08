/**
 * Une quantité saisie en kilos, en bobines ou en palettes (ECRANS-PRO § 3, P3) : le stock est
 * toujours en kilos, la saisie dans l'unité qu'on compte. Le composant rend des **kilos**
 * (`onChange(kg)`), dit la conversion (« 3 bobines = 7,49 kg ») et, quand on change d'unité,
 * l'arrondi qu'elle a fait (« arrondi : 7,49 kg au lieu de 7,5 kg »). Avec `borne` (ce qui est
 * parti, ce qui reste), une conversion arrondit **vers le bas** pour ne jamais la dépasser.
 *
 * `tactile` : la version de l'atelier (`Compteur`, `SegmentsTactiles`).
 */
import { useState } from 'react'

import { kgEtMetres } from '../../lib/format'
import {
  depuisKg,
  direArrondi,
  direConversion,
  libelleUnite,
  toutRendre,
  unitesPossibles,
  versKg,
  type Conditionnement,
  type Unite,
} from '../../lib/unites'
import { Compteur } from '../atelier/Compteur'
import { SegmentsTactiles } from '../atelier/SegmentsTactiles'
import { Nombre } from './Nombre'
import styles from './Quantite.module.css'
import { Segments } from './Segments'

export interface QuantiteProps {
  kg: number | null
  onChange: (kg: number | null) => void
  unite: Unite
  onUnite: (unite: Unite) => void
  libelle: string
  poidsBobine?: number | null
  bobinesPalette?: number | null
  kgParMl?: number | null
  /** Le plus qu'on puisse saisir, en kilos (une conversion arrondit alors vers le bas). */
  borne?: number
  tactile?: boolean
}

/** La quantité dans l'unité, depuis des kilos ; `null` si rien n'est saisi. */
function enUnite(kg: number | null, unite: Unite, c: Conditionnement): number | null {
  if (kg == null) return null
  return depuisKg(kg, unite, c)?.quantite ?? kg
}

/** La conversion vers une autre unité, bornée vers le bas quand une borne est donnée. */
export function convertirBorne(kg: number, u: Unite, c: Conditionnement, borne?: number) {
  const conversion = depuisKg(kg, u, c)
  if (!conversion || borne == null || conversion.kg <= borne) return conversion
  const q = toutRendre(c, borne, u)
  const k = versKg(q, u, c) ?? 0
  return { quantite: q, kg: k, arrondi: Math.abs(k - kg) >= 0.0005 }
}

/** La quantité dans l'unité, les changements, et l'arrondi à dire. */
function useQuantite(props: QuantiteProps, c: Conditionnement) {
  const { kg, onChange, unite, onUnite, borne } = props
  const [arrondiDit, setArrondiDit] = useState('')
  const changerQuantite = (q: number | null) => {
    setArrondiDit('')
    onChange(q == null ? null : versKg(q, unite, c))
  }
  const changerUnite = (u: Unite) => {
    onUnite(u)
    if (kg == null) return setArrondiDit('')
    const conversion = convertirBorne(kg, u, c, borne)
    setArrondiDit(direArrondi(conversion, kg))
    if (conversion) onChange(conversion.kg)
  }
  return { quantite: enUnite(kg, unite, c), arrondiDit, changerQuantite, changerUnite }
}

export function Quantite(props: QuantiteProps) {
  const { kg, unite, libelle, borne, tactile } = props
  const c: Conditionnement = {
    poidsBobine: props.poidsBobine,
    bobinesPalette: props.bobinesPalette,
    kgParMl: props.kgParMl,
  }
  const { quantite, arrondiDit, changerQuantite, changerUnite } = useQuantite(props, c)
  const unites = unitesPossibles(c)
  const options = unites.map((u) => ({ valeur: u, libelle: tactile ? libelleCourt(u) : libelleUnite(c, u) }))
  const conversion = quantite == null ? '' : direConversion(quantite, unite, c)
  const ml = kg != null && c.kgParMl ? kgEtMetres(kg, c.kgParMl, tactile) : ''
  const max = borne == null ? undefined : (enUnite(borne, unite, c) ?? undefined)
  const ChoixUnite = tactile ? SegmentsTactiles : Segments
  return (
    <div className={tactile ? styles.tactile : styles.quantite}>
      <div className={styles.rangee}>
        {tactile ? (
          <Compteur valeur={quantite} onChange={changerQuantite} libelle={libelle} unite={unite} max={max} />
        ) : (
          <Nombre
            valeur={quantite}
            onChange={changerQuantite}
            libelle={libelle}
            min={0}
            max={max}
            decimales={unite === 'bobine' ? 0 : 3}
          />
        )}
        {unites.length > 1 ? (
          <ChoixUnite
            valeur={unite}
            options={options}
            onChange={changerUnite}
            libelle={`Unité de ${libelle}`}
          />
        ) : (
          <span className={styles.unite}>kg</span>
        )}
      </div>
      {conversion || ml || arrondiDit ? (
        <p className={styles.note} aria-live="polite">
          {[conversion, unite === 'kg' ? ml : '', arrondiDit].filter(Boolean).join(' · ')}
        </p>
      ) : null}
    </div>
  )
}

function libelleCourt(u: Unite): string {
  return u === 'kg' ? 'kg' : u === 'bobine' ? 'Bobines' : 'Palettes'
}
