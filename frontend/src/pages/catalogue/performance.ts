/**
 * La performance des fournisseurs (route 215, `GET /fournisseurs/performance`, lot D8) : OTIF et
 * score, rapprochés de la fiche **par identifiant** (P7-25, H-31). Tant que la route n'est pas
 * publiée, sa forme est celle de Gestion MP (PROVISOIRE : à remplacer par
 * `Schema<'PerformanceFournisseurs'>`), et une lecture refusée laisse « — » sans bloquer l'écran.
 */
import { useLecture } from '../../lib/requetes'

export interface ScoreFournisseur {
  fournisseur_id?: number | null
  fournisseur: string
  receptions: number
  otif: number | null
  score: number | null
  classement: string
  action: string
}

export interface Performance {
  cible_otif: number
  lignes: ScoreFournisseur[]
}

export function usePerformance() {
  return useLecture<Performance>('/fournisseurs/performance', undefined, { staleTime: 60_000 })
}

/** Le score d'un fournisseur, par son identifiant (jamais par son nom). */
export function scoreDe(p: Performance | undefined, id: number): ScoreFournisseur | null {
  return p?.lignes.find((l) => l.fournisseur_id === id) ?? null
}
