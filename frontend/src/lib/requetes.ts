/**
 * Les données du serveur tenues à jour (TanStack Query 5), ARCHITECTURE § 10.1.
 *
 * - Une clé par route d'API : `[chemin]` ou `[chemin, paramètres]`.
 * - Relance **sur le statut** seulement : une fois, si le serveur n'a pas répondu (statut 0) ou a
 *   failli (5xx) ; jamais sur un refus (4xx : 401, 403, 404, 409, 422, 429…), qui ne changera pas
 *   en réessayant. Gestion MP décidait sur le texte du message (P1-1) : c'est fini.
 * - Une écriture ne se relance jamais d'elle-même (elle n'est pas forcément sans effet la 2ᵉ fois).
 * - Après chaque écriture réussie, **toutes** les lectures ouvertes se relisent (invalidation
 *   globale), et l'écriture ne se termine qu'une fois les données relues : la fiche qu'on rouvre
 *   montre déjà les chiffres à jour (REGLES-ECRAN § 3, « Chargement honnête »).
 * - Sans réseau, la lecture échoue (« Le serveur ne répond pas… ») au lieu d'attendre en silence
 *   (`networkMode: 'always'`) : « Pas de réseau » se dit comme tel, distinct d'une liste vide.
 * - Données fraîches 15 s ; relues au retour sur l'onglet et au retour du réseau (comme Gestion MP).
 */
import {
  MutationCache,
  QueryClient,
  useMutation,
  useQuery,
  type QueryKey,
  type UseQueryOptions,
} from '@tanstack/react-query'

import { api, ErreurApi } from './api'

type Parametres = Record<string, string | number | boolean | null | undefined | (string | number)[]>

/** Le nombre de relances d'une lecture qui a échoué pour une raison passagère. */
export const RELANCES = 1

/** Faut-il relancer ? Seulement sur un statut passager (0 ou 5xx), et une fois. */
export function relancer(echecs: number, erreur: unknown): boolean {
  return echecs < RELANCES && erreur instanceof ErreurApi && erreur.passagere
}

/** La clé d'une lecture : la route, puis ses paramètres s'il y en a. */
export function cleApi(chemin: string, params?: Parametres): QueryKey {
  return params && Object.keys(params).length ? [chemin, params] : [chemin]
}

declare module '@tanstack/react-query' {
  interface Register {
    mutationMeta: { invalider?: boolean }
  }
}

/** Le client de requêtes de l'application (un seul, créé au démarrage ; un par essai). */
export function creerClientRequetes({ delaiRelance = 1000 }: { delaiRelance?: number } = {}): QueryClient {
  const client: QueryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 15_000,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        networkMode: 'always',
        retry: relancer,
        retryDelay: delaiRelance,
      },
      mutations: { retry: false, networkMode: 'always' },
    },
    mutationCache: new MutationCache({
      // Rendre la promesse fait attendre la relecture avant de rendre la main à l'écran.
      onSuccess: (_donnees, _entree, _contexte, mutation) =>
        mutation.meta?.invalider === false ? undefined : client.invalidateQueries(),
    }),
  })
  return client
}

type OptionsLecture<T> = Omit<UseQueryOptions<T, ErreurApi>, 'queryKey' | 'queryFn'>

/**
 * Lit une route GET et la tient à jour. `chemin` à `null` : rien à lire pour l'instant (une fiche
 * pas encore choisie).
 */
export function useLecture<T>(chemin: string | null, params?: Parametres, options: OptionsLecture<T> = {}) {
  return useQuery<T, ErreurApi>({
    ...options,
    queryKey: cleApi(chemin ?? '', params),
    queryFn: ({ signal }) =>
      chemin == null
        ? Promise.reject(new ErreurApi('Rien à lire.', 400))
        : api.get<T>(chemin, params, signal),
    enabled: chemin != null && (options.enabled ?? true),
  })
}

/**
 * Une écriture (POST, PUT, DELETE). Réussie, elle relit toutes les données ouvertes, sauf
 * `invalider: false` (la connexion, qui recharge la session elle-même).
 */
export function useEcriture<E = void, R = unknown>(
  ecrire: (entree: E) => Promise<R>,
  { invalider = true }: { invalider?: boolean } = {},
) {
  return useMutation<R, ErreurApi, E>({ mutationFn: ecrire, meta: { invalider } })
}
