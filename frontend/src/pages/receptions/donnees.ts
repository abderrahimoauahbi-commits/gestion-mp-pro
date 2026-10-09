/**
 * Les lectures des réceptions, réclamations, pesées et bobines : une clé par route (TanStack
 * Query). Une écriture relit tout (invalidation globale de `useEcriture`).
 */
import { keepPreviousData } from '@tanstack/react-query'

import { useLecture } from '../../lib/requetes'
import type { CommandeResume } from '../commandes/types'
import type { Matiere } from '../plan-achat/types'
import type {
  EvolutionBobines,
  Fournisseur,
  Magasin,
  Motifs,
  ReceptionFiche,
  ReceptionResume,
  ReclamationFiche,
  ReclamationResume,
} from './types'

export const useReceptions = () => useLecture<ReceptionResume[]>('/receptions')

/** Les réceptions que la recherche du serveur trouve (lignes, lots, références compris). */
export const useReceptionsTrouvees = (q: string) =>
  useLecture<ReceptionResume[]>(
    q.trim() ? '/receptions' : null,
    { q: q.trim() },
    { placeholderData: keepPreviousData },
  )

/** Une fiche ; un brouillon se relit toutes les 30 s (le serveur le remet à jour). */
export const useReception = (id: number | null) =>
  useLecture<ReceptionFiche>(id == null ? null : `/receptions/${id}`, undefined, {
    refetchInterval: (q) => (q.state.data?.statut === 'brouillon' ? 30_000 : false),
  })

export const useReclamations = () => useLecture<ReclamationResume[]>('/reclamations')

export const useReclamation = (id: number | null) =>
  useLecture<ReclamationFiche>(id == null ? null : `/reclamations/${id}`)

export const useBobines = () => useLecture<EvolutionBobines>('/receptions/bobines')

export const useMotifs = () => useLecture<Motifs>('/motifs')

export const useMagasins = () => useLecture<Magasin[]>('/magasins')

export const useFournisseursActifs = () => useLecture<Fournisseur[]>('/fournisseurs', { actif: true })

export const useMatieresActives = () => useLecture<Matiere[]>('/matieres', { actif: true })

/** Tous les bons (la saisie y cherche ceux qui attendent une livraison). */
export const useBons = () => useLecture<CommandeResume[]>('/commandes')
