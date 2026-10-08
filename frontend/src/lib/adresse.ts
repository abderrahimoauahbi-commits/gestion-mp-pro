/**
 * L'état d'un écran vit dans son adresse (ARCHITECTURE § 10.1, REGLES-ECRAN § 2) : onglet,
 * recherche, filtres, fiche ouverte. Copier-coller un lien rouvre la même vue ; un raccourci d'un
 * autre écran pose son filtre (M74) ; fermer une fiche rend la liste telle qu'on l'avait laissée.
 *
 * - `?onglet=` : l'onglet ouvert (`useOngletAdresse`).
 * - `?q=` : la recherche (`useRechercheAdresse`), écrite à la frappe sans remplir l'historique.
 * - filtres nommés (`useFiltresAdresse`) : `?fournisseur=12&statut=envoyee`.
 * - fiche par adresse stable (A5) : `/commandes/12` = la liste des commandes et la fiche 12 en
 *   fenêtre ; fermer revient à `/commandes` avec le même `?onglet=`, `?q=` et les mêmes filtres
 *   (`useFicheAdresse`). Ouvrir une fiche est une navigation : « Précédent » la referme.
 */
import { useCallback } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

/** Les paramètres avec `cle` posé à `valeur` (retiré si vide), sans toucher aux autres. */
export function avecParametre(params: URLSearchParams, cle: string, valeur: string | null | undefined) {
  const suite = new URLSearchParams(params)
  if (valeur == null || valeur === '') suite.delete(cle)
  else suite.set(cle, valeur)
  return suite
}

/** L'onglet ouvert, lu et écrit dans `?onglet=` ; un onglet inconnu de l'adresse rend `defaut`. */
export function useOngletAdresse<T extends string>(
  permis: readonly T[],
  defaut: T,
): [T, (onglet: T) => void] {
  const [params, setParams] = useSearchParams()
  const demande = params.get('onglet')
  const actif = permis.find((p) => p === demande) ?? defaut
  const choisir = useCallback(
    (onglet: T) =>
      setParams((p) => avecParametre(p, 'onglet', onglet === defaut ? null : onglet), { replace: true }),
    [setParams, defaut],
  )
  return [actif, choisir]
}

/** La recherche de l'écran, dans `?q=` ; chaque frappe remplace l'adresse (l'historique ne grossit pas). */
export function useRechercheAdresse(): [string, (q: string) => void] {
  const [params, setParams] = useSearchParams()
  const poser = useCallback(
    (q: string) => setParams((p) => avecParametre(p, 'q', q), { replace: true }),
    [setParams],
  )
  return [params.get('q') ?? '', poser]
}

export interface FiltresAdresse<K extends string> {
  /** La valeur d'un filtre ('' s'il n'est pas posé). */
  valeur: (cle: K) => string
  /** Les filtres posés seulement. */
  poses: Partial<Record<K, string>>
  poser: (cle: K, valeur: string | null) => void
  /** « Effacer les filtres » : retire les filtres, garde l'onglet et la recherche. */
  effacer: () => void
  /** Le nombre de filtres posés (« N critère(s) »). */
  nombre: number
}

/** Des filtres nommés, dans l'adresse (`cles` : les paramètres que l'écran reconnaît). */
export function useFiltresAdresse<K extends string>(cles: readonly K[]): FiltresAdresse<K> {
  const [params, setParams] = useSearchParams()
  const signature = cles.join('|')
  const poser = useCallback(
    (cle: K, valeur: string | null) => setParams((p) => avecParametre(p, cle, valeur), { replace: true }),
    [setParams],
  )
  const effacer = useCallback(
    () =>
      setParams(
        (p) => {
          const suite = new URLSearchParams(p)
          for (const c of signature.split('|')) suite.delete(c)
          return suite
        },
        { replace: true },
      ),
    [setParams, signature],
  )
  const poses: Partial<Record<K, string>> = {}
  for (const c of cles) {
    const v = params.get(c)
    if (v) poses[c] = v
  }
  return {
    valeur: (cle: K) => params.get(cle) ?? '',
    poses,
    poser,
    effacer,
    nombre: Object.keys(poses).length,
  }
}

export interface FicheAdresse {
  /** L'identifiant de la fiche ouverte, `null` si aucune (ou `nouveau`). */
  id: number | null
  /** Vrai sur `/<base>/nouveau` (saisie d'un nouveau document). */
  nouveau: boolean
  ouvrir: (id: number | 'nouveau') => void
  fermer: () => void
}

/**
 * La fiche ouverte par-dessus une liste, à adresse stable. `base` : le chemin de la liste
 * (`/commandes`) ; la route déclare `/commandes/:id`. L'onglet, la recherche et les filtres de
 * l'adresse sont gardés à l'ouverture comme à la fermeture.
 */
export function useFicheAdresse(base: string, parametre = 'id'): FicheAdresse {
  const valeur = useParams()[parametre]
  const navigate = useNavigate()
  const { search } = useLocation()
  const id = valeur && /^\d+$/.test(valeur) ? Number(valeur) : null
  const ouvrir = useCallback(
    (cible: number | 'nouveau') => navigate(`${base}/${cible}${search}`),
    [navigate, base, search],
  )
  const fermer = useCallback(() => navigate(`${base}${search}`), [navigate, base, search])
  return { id, nouveau: valeur === 'nouveau', ouvrir, fermer }
}
