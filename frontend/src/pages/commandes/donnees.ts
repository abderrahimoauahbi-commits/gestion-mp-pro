/**
 * Les lectures des commandes : une clé par route (TanStack Query). La liste se lit entière (les
 * indicateurs comptent tous les bons, quels que soient l'onglet, la recherche et les filtres).
 */
import { useLecture } from '../../lib/requetes'
import type { CommandeFiche, CommandeResume } from './types'

export const useCommandes = () => useLecture<CommandeResume[]>('/commandes')

/** La fiche d'un bon ; relue au retour sur l'onglet et après chaque écriture. */
export const useCommande = (id: number | null) =>
  useLecture<CommandeFiche>(id == null ? null : `/commandes/${id}`)
