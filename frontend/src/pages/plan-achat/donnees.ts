/**
 * Les lectures du plan d'achat et de la préparation : une clé par route (TanStack Query). Une
 * écriture relit tout (invalidation globale de `useEcriture`).
 */
import { useLecture } from '../../lib/requetes'
import type { Devise, Matiere, PlanAchat, Preparation } from './types'

export const usePlanAchat = () => useLecture<PlanAchat>('/plan-achat')

export const usePreparation = (fournisseurId: number | null) =>
  useLecture<Preparation>(fournisseurId == null ? null : `/plan-achat/fournisseurs/${fournisseurId}`)

/** Les matières actives d'un fournisseur (ajout d'une ligne à la préparation ou au bon). */
export const useMatieresDuFournisseur = (fournisseurId: number | null) =>
  useLecture<Matiere[]>(fournisseurId == null ? null : '/matieres', {
    fournisseur: fournisseurId ?? undefined,
    actif: true,
  })

export const useDevises = () => useLecture<Devise[]>('/devises')
