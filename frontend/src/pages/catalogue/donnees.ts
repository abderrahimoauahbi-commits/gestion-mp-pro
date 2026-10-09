/**
 * Les lectures du catalogue : une clé par route (TanStack Query), partagée par la liste, les
 * fiches, les filtres et les compteurs des onglets (P7-17 : une requête, une clé). Une écriture
 * relit tout (invalidation globale de `useEcriture`).
 */
import { useLecture } from '../../lib/requetes'
import type {
  Classification,
  CodeDouanier,
  Devise,
  Fournisseur,
  FournisseurResume,
  Matiere,
  MatiereFiche,
} from './types'

export const useMatieres = () => useLecture<Matiere[]>('/matieres')

export const useMatiere = (id: number | null) =>
  useLecture<MatiereFiche>(id == null ? null : `/matieres/${id}`)

export const useClassification = (actif = true) =>
  useLecture<Classification>(actif ? '/classification' : null)

/** Les fournisseurs : complets pour la direction et les achats, résumés pour l'alimentation. */
export const useFournisseurs = () => useLecture<(Fournisseur | FournisseurResume)[]>('/fournisseurs')

export const useFournisseur = (id: number | null) =>
  useLecture<Fournisseur>(id == null ? null : `/fournisseurs/${id}`)

/** Les devises et les codes douaniers : direction et achats seulement (l'alimentation ne voit aucun prix). */
export const useDevises = (actif: boolean) => useLecture<Devise[]>(actif ? '/devises' : null)

export const useCodesDouaniers = (actif: boolean) =>
  useLecture<CodeDouanier[]>(actif ? '/codes-douaniers' : null)
