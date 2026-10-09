/**
 * Ce qui empêchera de valider une sortie, dit en tête **avant** la saisie (bandeau) : un ordre
 * validé à une date plus récente (les numéros suivent les dates, M67), un inventaire qui compte
 * une matière de l'ordre dans ce magasin (périmètre, (b)). Le serveur le redit dans la
 * proposition (`blocages`) ; l'écran le calcule aussi pour un ordre hors recette.
 */
import { date } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { sansDoublon, suspensions, useMagasins } from './commun'
import type { OrdreResume } from './types'
import type { SaisieSortie } from './useSaisieSortie'

/** La date du dernier ordre validé ou annulé (un annulé garde son numéro). */
export function dernierOrdre(ordres: readonly OrdreResume[] | undefined): string | null {
  const dates = (ordres ?? []).filter((o) => o.statut !== 'brouillon').map((o) => o.date)
  return dates.length ? dates.reduce((a, b) => (a > b ? a : b)) : null
}

/** Le texte du bandeau quand la date est avant celle du dernier ordre validé. */
export function blocageDate(jour: string, dernier: string | null): string {
  if (!dernier || jour >= dernier) return ''
  const d = date(dernier)
  return (
    `Un ordre du ${d} est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être ` +
    `daté avant. Pour un oubli, le dater du ${d} et écrire la vraie date dans les observations.`
  )
}

export function useEmpechements(s: SaisieSortie): string[] {
  const { contexte } = useSession()
  const ordres = useLecture<OrdreResume[]>('/ordres')
  const magasins = useMagasins()
  const nom = magasins.data?.find((m) => m.id === s.magasin)?.nom ?? ''
  const matieres = s.e.prises.map((p) => ({ id: p.matiere_id, reference: p.reference }))
  const serveur = s.e.demandeChangee ? [] : s.e.blocagesServeur
  return sansDoublon([
    blocageDate(s.e.jour, dernierOrdre(ordres.data)),
    ...serveur.filter((b) => !b.startsWith('Un ordre du ') && !b.startsWith("L'inventaire")),
    ...suspensions(contexte.inventaires_ouverts, matieres, nom ? [nom] : []),
    ...serveur.filter((b) => b.startsWith("L'inventaire") && !matieres.length),
  ])
}
