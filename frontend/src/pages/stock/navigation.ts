/**
 * Les adresses du Stock (ECRANS-PRO partie 2, A5) : la liste `/stock?onglet=…` et, par-dessus, la
 * fiche d'une matière (`/stock/matieres/:id`), la fiche d'un lot (`/lots/:id`) ou le suivi de
 * traçabilité (`/tracabilite?lot=|ordre=|matiere=`). Ouvrir une fiche garde l'onglet, la recherche
 * et les filtres de la liste ; la fermer les rend.
 *
 * - Chaque onglet garde sa recherche : `?q=` est celle de l'onglet ouvert, celle des autres attend
 *   dans `?q_<onglet>=` (un lien d'un autre écran pose `?q=` pour l'onglet qu'il ouvre).
 * - Le suivi garde dans l'adresse d'où l'on vient (`retour`, rouvert par × ou Échap) et le chemin
 *   parcouru (`depuis`, « ← Revenir au lot N ») : le « Précédent » du navigateur le remonte aussi.
 */
import { useCallback } from 'react'
import { useLocation, useNavigate } from 'react-router'

import type { Suivi } from './donnees'

export const ONGLETS_STOCK = ['matieres', 'lots', 'mouvements', 'ordres', 'a-valider'] as const
export type OngletStock = (typeof ONGLETS_STOCK)[number]

/** Ce que l'adresse ouvre par-dessus la liste. */
export type OuvertStock =
  { genre: 'matiere'; id: number } | { genre: 'lot'; id: number } | { genre: 'suivi'; suivi: Suivi } | null

const entier = (v: string | null | undefined) => (v && /^\d+$/.test(v) ? Number(v) : undefined)

/** Le suivi demandé par `?lot=`, `?ordre=` ou `?matiere=` (un seul, dans cet ordre). */
export function suiviDe(params: URLSearchParams): Suivi | null {
  const lot = entier(params.get('lot'))
  if (lot) return { lot }
  const ordre = entier(params.get('ordre'))
  if (ordre) return { ordre }
  const matiere = entier(params.get('matiere'))
  return matiere ? { matiere } : null
}

export function ouvertDe(chemin: string, params: URLSearchParams): OuvertStock {
  const m = /^\/stock\/matieres\/(\d+)$/.exec(chemin)
  if (m) return { genre: 'matiere', id: Number(m[1]) }
  const l = /^\/lots\/(\d+)$/.exec(chemin)
  if (l) return { genre: 'lot', id: Number(l[1]) }
  if (chemin === '/tracabilite') {
    const suivi = suiviDe(params)
    return suivi ? { genre: 'suivi', suivi } : null
  }
  return null
}

const estOnglet = (v: string | null): v is OngletStock => ONGLETS_STOCK.some((o) => o === v)

/** L'onglet de l'adresse ; les anciennes (`?volet=`, `?onglet=tracabilite`) mènent aux nouveaux. */
export function ongletDe(params: URLSearchParams, defaut: OngletStock = 'matieres'): OngletStock {
  const demande = params.get('onglet') ?? params.get('volet')
  if (demande === 'tracabilite') return 'ordres'
  return estOnglet(demande) ? demande : defaut
}

/** L'onglet de la liste sous une fiche : celui de l'adresse, ou celui que la fiche impose. */
export function ongletSous(ouvert: OuvertStock, params: URLSearchParams): OngletStock {
  if (ouvert?.genre === 'matiere') return 'matieres'
  if (ouvert?.genre === 'lot') return ongletDe(params, 'lots')
  if (ouvert?.genre === 'suivi') {
    // Sous le suivi, la liste d'où l'on vient (sa fiche, son onglet) ; sinon les ordres.
    const [chemin = '', requete = ''] = (params.get('retour') ?? '').split('?')
    const avant = new URLSearchParams(requete)
    const sous = ouvertDe(chemin, avant)
    if (chemin === '/stock' || (sous && sous.genre !== 'suivi')) return ongletSous(sous, avant)
    return 'ordres'
  }
  return ongletDe(params)
}

/** Les paramètres propres au suivi, retirés de l'adresse de la liste. */
const PARAMETRES_SUIVI = ['lot', 'ordre', 'retour', 'depuis', 'tvue']

/** La chaîne de requête d'une liste (sans `?` si vide). */
const texte = (p: URLSearchParams) => {
  const t = p.toString()
  return t ? `?${t}` : ''
}

/** Changer d'onglet : la recherche de l'onglet quitté attend dans `q_<onglet>`. */
export function parametresOnglet(search: string, depuis: OngletStock, vers: OngletStock): string {
  const p = new URLSearchParams(search)
  const q = p.get('q')
  p.delete('q')
  if (q) p.set(`q_${depuis}`, q)
  const reprise = p.get(`q_${vers}`)
  p.delete(`q_${vers}`)
  if (reprise) p.set('q', reprise)
  p.delete('onglet')
  p.delete('volet')
  if (vers !== 'matieres') p.set('onglet', vers)
  return texte(p)
}

/** La liste sous une fiche (pour la fermer) : l'onglet écrit seulement s'il n'est pas le premier. */
export function adresseListe(search: string, onglet: OngletStock): string {
  const p = new URLSearchParams(search)
  p.delete('onglet')
  p.delete('volet')
  if (onglet !== 'matieres') p.set('onglet', onglet)
  return `/stock${texte(p)}`
}

/** Le code d'un suivi dans le chemin parcouru (`lot:12`, `ordre:5`, `matiere:7`). */
export function codeSuivi(s: Suivi): string {
  if (s.lot) return `lot:${s.lot}`
  if (s.ordre) return `ordre:${s.ordre}`
  return `matiere:${s.matiere ?? 0}`
}

/** L'adresse d'un suivi. `retour` : où rendre la main à la fermeture ; `depuis` : le chemin. */
export function adresseSuivi(s: Suivi, retour?: string, depuis: readonly string[] = []): string {
  const p = new URLSearchParams()
  if (s.lot) p.set('lot', String(s.lot))
  else if (s.ordre) p.set('ordre', String(s.ordre))
  else if (s.matiere) p.set('matiere', String(s.matiere))
  if (depuis.length) p.set('depuis', depuis.join(','))
  if (retour) p.set('retour', retour)
  return `/tracabilite${texte(p)}`
}

/** Les gestes de navigation du Stock. */
export function useNavigationStock(onglet: OngletStock) {
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const avecOnglet = useCallback(
    (chemin: string) => {
      const p = new URLSearchParams(search)
      for (const c of PARAMETRES_SUIVI) p.delete(c)
      p.set('onglet', onglet)
      return `${chemin}${texte(p)}`
    },
    [search, onglet],
  )
  return {
    ouvrirMatiere: (id: number) => navigate(avecOnglet(`/stock/matieres/${id}`)),
    ouvrirLot: (id: number) => navigate(avecOnglet(`/lots/${id}`)),
    /** Le suivi, par-dessus ce qui est ouvert ; × y revient. */
    suivre: (s: Suivi) => navigate(adresseSuivi(s, `${pathname}${search}`)),
    fermer: () => navigate(adresseListe(search, onglet)),
    choisir: (vers: OngletStock) =>
      navigate(`/stock${parametresOnglet(search, onglet, vers)}`, { replace: true }),
  }
}
