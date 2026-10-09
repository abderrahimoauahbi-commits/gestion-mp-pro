/**
 * Les lectures des qualités : une clé par route (TanStack Query), partagée par les listes, la
 * fiche et les indicateurs. Les coûts et prix sont retirés par le serveur pour l'alimentation.
 */
import { useLecture } from '../../lib/requetes'
import type { Nomenclature, Qualite, QualiteFiche, VersionPlan, VersionRecette } from './types'

export const useQualites = () => useLecture<Qualite[]>('/qualites')

export const useQualite = (id: number | null) =>
  useLecture<QualiteFiche>(id == null ? null : `/qualites/${id}`)

export const useNomenclature = () => useLecture<Nomenclature>('/nomenclature')

export const useVersions = (id: number) => useLecture<VersionRecette[]>(`/qualites/${id}/versions`)

export const useVersionsPlan = (id: number) => useLecture<VersionPlan[]>(`/qualites/${id}/plan/versions`)
