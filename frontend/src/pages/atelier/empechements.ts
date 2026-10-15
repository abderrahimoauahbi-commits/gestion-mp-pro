/**
 * Ce qui empêchera de valider une sortie, dit en tête **avant** la saisie (bandeau) : un ordre
 * validé à une date plus récente (les numéros suivent les dates, M67), un inventaire qui compte
 * une matière de l'ordre dans ce magasin (périmètre, (b)). Le serveur le redit dans la
 * proposition (`blocages`) ; l'écran le calcule aussi pour un ordre hors recette. Les phrases et
 * la règle du dernier ordre sont celles du moteur unique `lib/ordre.ts`.
 */
import { useDernierOrdre } from '../../lib/dernierOrdre'
import { blocageDate } from '../../lib/ordre'
import { useSession } from '../../lib/session'
import { sansDoublon, suspensions, useMagasins } from './commun'
import type { SaisieSortie } from './useSaisieSortie'

export function useEmpechements(s: SaisieSortie): string[] {
  const { contexte } = useSession()
  const dernier = useDernierOrdre()
  const magasins = useMagasins()
  const nom = magasins.data?.find((m) => m.id === s.magasin)?.nom ?? ''
  const matieres = s.e.prises.map((p) => ({ id: p.matiere_id, reference: p.reference }))
  const serveur = s.e.demandeChangee ? [] : s.e.blocagesServeur
  return sansDoublon([
    blocageDate(s.e.jour, dernier),
    ...serveur.filter((b) => !b.startsWith('Un ordre du ') && !b.startsWith("L'inventaire")),
    ...suspensions(contexte.inventaires_ouverts, matieres, nom ? [nom] : []),
    ...serveur.filter((b) => b.startsWith("L'inventaire") && !matieres.length),
  ])
}
