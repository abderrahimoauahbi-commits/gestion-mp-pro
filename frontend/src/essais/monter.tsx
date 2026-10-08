/**
 * Outils d'essai de la coque (lot E2) : un faux serveur conforme au contrat des routes 1–22 et
 * 49–56 (API-PRO), et le montage de l'application entière dans un routeur de mémoire. Les lots F
 * s'en servent pour essayer leurs pages dans la coque, au rôle voulu.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import { creerRoutes } from '../App'
import { ECRANS } from '../routes'
import { LIBELLES_ROLES } from '../lib/droits'
import { creerClientRequetes } from '../lib/requetes'
import { SessionFournie, type Session } from '../lib/session'
import type { Contexte, Moi } from '../lib/types-provisoires-s2'
import type { Role } from '../lib/types'

export type Reponse =
  { statut?: number; corps?: unknown } | ((corps: unknown, url: URL) => { statut?: number; corps?: unknown })

/** Le compte d'essai d'un rôle. */
export function moiDe(role: Role, autres: Partial<Moi> = {}): Moi {
  const noms: Record<Role, string> = {
    direction: 'MAZARI',
    achats: 'Karim BENALI',
    alimentation: 'Ahmed',
    administrateur: 'Service informatique',
  }
  return {
    id: { direction: 1, achats: 2, alimentation: 3, administrateur: 5 }[role],
    identifiant: noms[role].split(' ')[0]?.toLowerCase() ?? role,
    nom: noms[role],
    role,
    role_libelle: LIBELLES_ROLES[role],
    email: '',
    voit_prix: role === 'direction' || role === 'achats',
    version: 1,
    ...autres,
  }
}

/** Le contexte d'essai d'un rôle (GET /contexte). */
export function contexteDe(role: Role, autres: Partial<Contexte> = {}): Contexte {
  return {
    moi: moiDe(role),
    societe: 'Tapis de l’Atlas',
    date_cloture: null,
    inventaires_ouverts: [],
    compteurs: { alerte_rouge: 7, anomalies: 3, a_approuver: 2, receptions_brouillon: 4 },
    alerte_serveur: null,
    ...autres,
  }
}

export interface Appel {
  methode: string
  chemin: string
  corps: unknown
}

/**
 * Remplace `fetch` par un faux serveur : `reponses['GET /contexte']` → réponse. Une route absente
 * répond 404 au format des refus. Rend la liste des appels reçus.
 */
export function fauxServeur(reponses: Record<string, Reponse>): Appel[] {
  const appels: Appel[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (entree: string, init: RequestInit = {}) => {
      const url = new URL(entree, 'http://localhost')
      const methode = init.method ?? 'GET'
      const chemin = url.pathname.replace(/^\/api/, '')
      const corps = typeof init.body === 'string' ? JSON.parse(init.body) : undefined
      appels.push({ methode, chemin: `${chemin}${url.search}`, corps })
      const r = reponses[`${methode} ${chemin}`]
      const { statut = 200, corps: sortie } =
        typeof r === 'function'
          ? r(corps, url)
          : (r ?? { statut: 404, corps: { detail: 'Introuvable.', code: 'introuvable' } })
      if (statut === 204) return new Response(null, { status: 204 })
      return Response.json(sortie ?? null, { status: statut })
    }),
  )
  return appels
}

/** Les réponses d'une session ouverte au rôle donné (contexte, notifications, recherche vides). */
export function reponsesConnecte(role: Role, autres: Record<string, Reponse> = {}): Record<string, Reponse> {
  return {
    'GET /contexte': { corps: contexteDe(role) },
    'GET /notifications': { corps: { elements: [], total: 0, suivant: null, non_lues: 0 } },
    'GET /recherche': { corps: [] },
    'GET /etat': { corps: { installe: true, societe: 'Tapis de l’Atlas' } },
    'GET /visages': { corps: [] },
    ...autres,
  }
}

/** Monte l'application entière à une adresse ; rend le routeur (pour naviguer, lire l'adresse). */
export function monterApp(adresse: string) {
  const routeur = createMemoryRouter(creerRoutes(), { initialEntries: [adresse] })
  const client = creerClientRequetes({ delaiRelance: 0 })
  const rendu = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={routeur} />
    </QueryClientProvider>,
  )
  return {
    routeur,
    client,
    ...rendu,
    adresse: () => `${routeur.state.location.pathname}${routeur.state.location.search}`,
  }
}

/** Une session d'essai (sans serveur) pour monter un composant de la coque seul. */
export function sessionDe(role: Role, autres: Partial<Contexte> = {}): Session {
  const contexte = contexteDe(role, autres)
  return {
    contexte,
    moi: contexte.moi,
    role,
    deconnecter: vi.fn(async () => undefined),
    rafraichir: vi.fn(async () => undefined),
  }
}

/** Monte un composant dans une session, un client de requêtes et un routeur de mémoire. */
export function monterDansSession(
  element: ReactNode,
  role: Role,
  adresse = '/',
  autres: Partial<Contexte> = {},
) {
  const session = sessionDe(role, autres)
  const routeur = createMemoryRouter(
    [{ path: '*', element: <SessionFournie session={session}>{element}</SessionFournie> }],
    { initialEntries: [adresse] },
  )
  const client = creerClientRequetes({ delaiRelance: 0 })
  const rendu = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={routeur} />
    </QueryClientProvider>,
  )
  return { session, routeur, ...rendu }
}

/** Fait passer le poste pour un téléphone (étroit et tactile) ou un poste de bureau. */
export function poste(telephone: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((requete: string) => ({
      matches: telephone && /max-width: 700px/.test(requete) ? true : telephone && /1079/.test(requete),
      media: requete,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      addListener: () => undefined,
      removeListener: () => undefined,
      onchange: null,
      dispatchEvent: () => false,
    })),
  )
}

/**
 * Charge d'avance les pages de tous les écrans. Vitest évalue les modules importés à la demande
 * sans attendre un import identique encore en cours (un navigateur l'attend) : sans ce
 * préchargement, deux écrans « à venir » ouverts coup sur coup verraient un module à moitié prêt.
 */
export async function prechargerPages(): Promise<void> {
  await Promise.all(ECRANS.map((e) => e.page()))
}

/**
 * Un `localStorage` en mémoire : Node 22+ pose son propre `localStorage` (vide sans
 * `--localstorage-file`) par-dessus celui de jsdom.
 */
export function stockageMemoire(): Storage {
  const valeurs = new Map<string, string>()
  const stockage: Storage = {
    get length() {
      return valeurs.size
    },
    clear: () => valeurs.clear(),
    getItem: (cle) => valeurs.get(cle) ?? null,
    key: (i) => [...valeurs.keys()][i] ?? null,
    removeItem: (cle) => {
      valeurs.delete(cle)
    },
    setItem: (cle, valeur) => {
      valeurs.set(cle, String(valeur))
    },
  }
  vi.stubGlobal('localStorage', stockage)
  return stockage
}
