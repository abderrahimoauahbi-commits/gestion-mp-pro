/**
 * La référence composée, semi-automatique (route 75, `GET /matieres/reference`) : à chaque
 * changement de la classification, du code couleur ou du suffixe, le serveur compose la référence
 * (« PP FRZ-2900 Dtex-Gold 3423-Hs ») et la désignation, et dit si une matière la porte déjà.
 *
 * Une matière **nouvelle** prend la référence composée tant qu'on ne l'a pas retouchée à la main ;
 * une fois retouchée (ou pour une matière existante), la référence est libre et la composée est
 * seulement proposée (« la reprendre »). La demande part 250 ms après la dernière frappe.
 */
import { useEffect, useState } from 'react'

import { useLecture } from '../../lib/requetes'
import type { FormeMatiere } from './formeMatiere'
import type { Schema } from '../../lib/types'

export type ReferenceComposee = Schema<'ReferenceComposee'>

/** Le délai avant de demander la référence composée (ms). */
export const DELAI_COMPOSITION = 250

type Parties = Pick<
  FormeMatiere,
  'composition_id' | 'type_fil_id' | 'titrage_id' | 'couleur_id' | 'couleur_code' | 'suffixe'
>

/** Les paramètres de la demande, ou `null` si rien de la classification n'est choisi. */
export function parametresReference(f: Parties) {
  if (!f.composition_id && !f.type_fil_id && !f.titrage_id && !f.couleur_id) return null
  return {
    composition_id: f.composition_id ?? undefined,
    type_fil_id: f.type_fil_id ?? undefined,
    titrage_id: f.titrage_id ?? undefined,
    couleur_id: f.couleur_id ?? undefined,
    couleur_code: f.couleur_code.trim() || undefined,
    suffixe: f.suffixe.trim() || undefined,
  }
}

/** Une valeur qui ne suit la source qu'après `delai` ms de calme. */
function useApresCalme<T>(valeur: T, delai: number): T {
  const [calme, setCalme] = useState(valeur)
  const cle = JSON.stringify(valeur)
  useEffect(() => {
    const minuterie = setTimeout(() => setCalme(valeur), delai)
    return () => clearTimeout(minuterie)
    // La clé dit si la valeur a changé (un objet neuf à chaque rendu ne relance pas l'attente).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cle, delai])
  return calme
}

/**
 * La référence composée des parties de la forme ; `libre` faux : elle s'écrit dans la forme
 * (`appliquer`) dès qu'elle arrive.
 */
export function useReferenceComposee(
  f: FormeMatiere,
  libre: boolean,
  appliquer: (r: ReferenceComposee) => void,
): ReferenceComposee | null {
  const parametres = useApresCalme(parametresReference(f), DELAI_COMPOSITION)
  const lue = useLecture<ReferenceComposee>(parametres ? '/matieres/reference' : null, parametres ?? {})
  const composee = parametres ? (lue.data ?? null) : null
  const derniere = composee ? `${composee.reference}|${composee.designation}` : ''
  useEffect(() => {
    if (!libre && composee) appliquer(composee)
    // `appliquer` change à chaque rendu : la référence reçue (et la liberté) suffisent.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [derniere, libre])
  return composee
}
