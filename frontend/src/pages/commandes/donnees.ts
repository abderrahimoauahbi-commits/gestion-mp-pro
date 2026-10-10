/**
 * Les lectures des commandes : une clé par route (TanStack Query). La liste est **paginée au
 * serveur** (`useListePaginee`) ; l'aperçu (`/commandes/apercu`) porte les comptes par onglet, les
 * indicateurs (tous les bons ouverts), le pied de totaux et les options des filtres liés. Les bons
 * ouverts (`/commandes/ouverts`), bornés, servent la saisie des réceptions, Ma journée et le Cockpit.
 */
import { keepPreviousData } from '@tanstack/react-query'

import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import { useLecture } from '../../lib/requetes'
import type { ApercuCommandes, CommandeFiche, CommandeResume } from './types'

type Params = Record<string, string | number | boolean | null | undefined>

/** La liste des bons, page par page (recherche, filtres et « en retard » poussés au serveur). */
export const useListeCommandes = (params: Params) => useListePaginee<CommandeResume>('/commandes', params)

/** L'aperçu de la liste : comptes par onglet, indicateurs, pied, options des filtres liés. */
export const useApercuCommandes = (params: Params) =>
  useLecture<ApercuCommandes>('/commandes/apercu', params, { placeholderData: keepPreviousData })

/** Tous les bons ouverts (bornés) : la saisie des réceptions, Ma journée et le Cockpit les filtrent. */
export const useCommandesOuvertes = (lire = true) =>
  useLecture<CommandeResume[]>(lire ? '/commandes/ouverts' : null)

/** La fiche d'un bon ; relue au retour sur l'onglet et après chaque écriture. */
export const useCommande = (id: number | null) =>
  useLecture<CommandeFiche>(id == null ? null : `/commandes/${id}`)
