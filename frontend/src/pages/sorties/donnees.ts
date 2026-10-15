/**
 * Les formes et les lectures des ordres de fabrication (routes 134–144 du lot D6), lues dans
 * l'OpenAPI ; une clé par route.
 */
import { keepPreviousData } from '@tanstack/react-query'

import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'

export type OrdreResume = Schema<'OrdreResume'>
export type OrdreFiche = Schema<'OrdreFiche'>
export type ApercuOrdres = Schema<'ApercuOrdres'>
export type OptionOrdres = Schema<'OptionOrdres'>
export type LigneOrdre = Schema<'LigneOrdre'>
export type ParMatiere = Schema<'ParMatiere'>
export type Proposition = Schema<'Proposition'>
export type LigneProposee = Schema<'LigneProposee'>
export type LotPropose = Schema<'LotPropose'>
export type LotSorti = Schema<'LotSorti'>
export type QualiteResume = Schema<'QualiteResume'>
export type Metier = Schema<'MetierFiche'>
export type StatutOrdre = OrdreResume['statut']

type Params = Record<string, string | number | boolean | null | undefined>

/** L'aperçu de la liste des ordres (comptes d'onglet, agrégats, options des filtres liés). */
export const useApercuOrdres = (params: Params) =>
  useLecture<ApercuOrdres>('/ordres/apercu', params, { placeholderData: keepPreviousData })

export const useOrdre = (id: number | null) => useLecture<OrdreFiche>(id == null ? null : `/ordres/${id}`)

export const useQualites = () => useLecture<QualiteResume[]>('/qualites')

export const useMetiers = () => useLecture<Metier[]>('/metiers')

export const useLotsSortis = (id: number) => useLecture<LotSorti[]>(`/ordres/${id}/lots-sortis`)

/** « CODE · Nom » d'un métier, partout le même (H-39). */
export function nomMetier(m: Pick<Metier, 'code' | 'nom'>): string {
  return m.nom && m.nom !== m.code ? `${m.code} · ${m.nom}` : m.code
}

/** La date du dernier ordre validé ou annulé : la règle du moteur. */
export { dernierOrdre } from '../../lib/ordre'
