/**
 * La date du dernier ordre validé ou annulé (les numéros suivent les dates, M67), lue **sans
 * charger toute la liste des ordres** : la saisie (bureau et téléphone) n'en tirait que cette
 * date, et la liste entière pesait 3 Mo et 1,2 s au bout de trois ans (lot CONFORT-LENTEURS).
 * Les deux plus récents validés et les deux plus récents annulés (route 135, le plus récent
 * d'abord) suffisent, même en écartant l'ordre qu'on regarde (`sauf`) : le même `dernierOrdre`
 * que sur la liste entière. `null` tant qu'ils se lisent, comme avant.
 */
import { dernierOrdre } from './ordreBlocages'
import { useLecture } from './requetes'
import type { Page, Schema } from './types'

/** Combien d'ordres lire par statut : un de plus que celui qu'on peut écarter (`sauf`). */
export const DERNIERS = 2

type Ordre = Schema<'OrdreResume'>

export function useDernierOrdre(sauf?: number | null): string | null {
  const valides = useLecture<Page<Ordre>>('/ordres', { statut: 'valide', limite: DERNIERS })
  const annules = useLecture<Page<Ordre>>('/ordres', { statut: 'annule', limite: DERNIERS })
  if (!valides.data || !annules.data) return null
  return dernierOrdre([...valides.data.elements, ...annules.data.elements], sauf)
}
