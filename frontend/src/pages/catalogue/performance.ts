/**
 * La performance des fournisseurs (route 215, `GET /fournisseurs/performance`, lot D8) : OTIF et
 * score, rapprochés de la fiche **par identifiant** (P7-25, H-31). Une lecture refusée laisse « — »
 * sans bloquer l'écran.
 */
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'

export type ScoreFournisseur = Schema<'ScoreFournisseur'>
export type Performance = Schema<'PerformanceFournisseurs'>

export function usePerformance() {
  return useLecture<Performance>('/fournisseurs/performance', undefined, { staleTime: 60_000 })
}

/** Le score d'un fournisseur, par son identifiant (jamais par son nom). */
export function scoreDe(p: Performance | undefined, id: number): ScoreFournisseur | null {
  return p?.lignes.find((l) => l.fournisseur_id === id) ?? null
}
