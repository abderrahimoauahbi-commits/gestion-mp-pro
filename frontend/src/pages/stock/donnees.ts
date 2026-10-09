/**
 * Les lectures du stock : une clé par route (TanStack Query), partagée par les onglets, les fiches
 * et les compteurs. Une écriture relit tout (invalidation globale de `useEcriture`).
 */
import { useLecture } from '../../lib/requetes'
import type {
  Brouillons,
  EtatStock,
  FicheStockMatiere,
  LotFiche,
  LotSolde,
  Magasin,
  MatiereResume,
  Motifs,
  Tracabilite,
} from './types'

export const useEtatStock = () => useLecture<EtatStock>('/stock')

export const useFicheStock = (matiere: number | null) =>
  useLecture<FicheStockMatiere>(matiere == null ? null : `/stock/${matiere}`)

/**
 * Les lots ; `avecEpuises` : aussi ceux qui ne portent plus rien (le serveur ne rend par défaut
 * que les lots en stock ; `false` s'écrit en toutes lettres, `qs` saute un booléen faux).
 */
export const useLots = (avecEpuises: boolean) =>
  useLecture<LotSolde[]>('/lots', avecEpuises ? { non_nuls: 'false' } : {})

export const useLot = (id: number | null) => useLecture<LotFiche>(id == null ? null : `/lots/${id}`)

export const useMagasins = () => useLecture<Magasin[]>('/magasins')

/** Le catalogue (rôle, fournisseur, identifiants) : sans prix pour l'alimentation (filtre du serveur). */
export const useMatieres = () => useLecture<MatiereResume[]>('/matieres')

export const useMotifs = () => useLecture<Motifs>('/motifs', undefined, { staleTime: 600_000 })

export const useBrouillons = () => useLecture<Brouillons>('/brouillons')

export interface Suivi {
  lot?: number
  ordre?: number
  matiere?: number
}

export const useTracabilite = (suivi: Suivi | null) =>
  useLecture<Tracabilite>(suivi ? '/tracabilite' : null, {
    lot: suivi?.lot,
    ordre: suivi?.ordre,
    matiere: suivi?.matiere,
  })
