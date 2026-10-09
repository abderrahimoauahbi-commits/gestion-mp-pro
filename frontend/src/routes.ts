/**
 * Le registre unique des écrans (ECRANS-PRO § 4) : chemin, titre (= libellé du menu = titre de la
 * page), groupe du menu, rôles, clé d'aide, onglets. Le menu, le fil d'Ariane, la garde de route,
 * l'aide de l'écran, la recherche globale et les liens du Mode d'emploi en sont dérivés : un rôle
 * ne voit dans le menu que ce que la garde lui ouvrira, et un lien vers un écran refusé n'est pas
 * un lien.
 *
 * Chaque domaine déclare ses écrans dans `pages/<domaine>/ecrans.ts` (le lot F du domaine les
 * remplit) ; ce fichier les rassemble seul (`import.meta.glob`) : un lot F n'a jamais à l'éditer.
 * L'ordre du menu, lui, est fixé ici (`ORDRE_DU_MENU`, tableau de ECRANS-PRO § 2.1).
 */
import type { ComponentType } from 'react'

import type aide from './aide.json'
import type { Role } from './lib/types'

/** Les groupes du menu, dans l'ordre de la barre latérale. */
export const GROUPES = ['Tous les jours', 'Achats', 'Stock', 'Référentiels', 'Pilotage', 'Aide'] as const
export type Groupe = (typeof GROUPES)[number]

/** Une section « écran » de `aide.json` : le compilateur refuse une clé qui n'y est pas. */
export type CleAide = keyof (typeof aide)['ecran']

export interface OngletEcran {
  cle: string
  libelle: string
  /** Libellé court quand le complet est long (le complet va en infobulle). */
  court?: string
  /** Rôles qui voient cet onglet ; absent : tous ceux de l'écran. */
  roles?: readonly Role[]
}

export interface Ecran {
  /** Chemin de l'écran (`/commandes`, `/commandes/:id`). */
  chemin: string
  /** Titre de la page = libellé du menu (une seule source). */
  titre: string
  /** Groupe du menu : présent = entrée de menu. */
  groupe?: Groupe
  /** Infobulle du menu quand le titre abrège ce que contient l'écran. */
  detail?: string
  /** Rôles à qui l'écran est ouvert (garde de route et menu) ; la direction y est nommée. */
  roles: readonly Role[]
  /** Section de `aide.json` (« ? » de l'en-tête, Mode d'emploi, NOTICE). */
  aide: CleAide
  onglets?: readonly OngletEcran[]
  /** Pour une fiche en fenêtre : la liste dessous (fil d'Ariane, entrée de menu active). */
  parent?: string
  /** Écran du téléphone : hors de la coque du bureau. */
  atelier?: true
  /** Le lot qui réalise la page (tant qu'elle est « à venir »). */
  lot?: string
  /** La page, chargée à la demande. */
  page: () => Promise<{ default: ComponentType }>
}

const MODULES = import.meta.glob<{ ecrans: readonly Ecran[] }>('./pages/*/ecrans.ts', { eager: true })

/** Tous les écrans déclarés par les domaines. */
export const ECRANS: readonly Ecran[] = Object.values(MODULES).flatMap((m) => m.ecrans)

/** L'ordre des entrées du menu (ECRANS-PRO § 2.1) ; chaque écran qui a un groupe y figure. */
export const ORDRE_DU_MENU: readonly string[] = [
  '/accueil',
  '/cockpit',
  '/stock',
  '/sorties',
  '/production',
  '/atelier',
  '/plan-achat',
  '/commandes',
  '/receptions',
  '/importations',
  '/inventaire',
  '/operations',
  '/catalogue',
  '/qualites',
  '/metiers',
  '/analyse',
  '/reglages',
  '/administration',
  '/aide',
]

/** Les écrans du menu, dans l'ordre du menu. */
export function entreesDuMenu(): Ecran[] {
  return ORDRE_DU_MENU.flatMap((chemin) => ECRANS.filter((e) => e.groupe && e.chemin === chemin))
}

/** L'écran déclaré à ce chemin exact (`/commandes/:id`), s'il existe. */
export function ecranParChemin(chemin: string): Ecran | undefined {
  return ECRANS.find((e) => e.chemin === chemin)
}

/** Les segments d'un chemin, sans les barres vides. */
const segments = (chemin: string) => chemin.split('/').filter(Boolean)

/** Vrai si l'adresse `pathname` répond au motif `chemin` (`:id` = un segment quelconque). */
export function correspond(chemin: string, pathname: string): boolean {
  const motif = segments(chemin)
  const reel = segments(pathname)
  return motif.length === reel.length && motif.every((m, i) => m.startsWith(':') || m === reel[i])
}

/**
 * L'écran qui sert une adresse (`/commandes/12?onglet=prix` → `/commandes/:id`). Un chemin sans
 * paramètre passe avant un chemin à paramètre (`/commandes/nouvelle` avant `/commandes/:id`).
 */
export function ecranDeAdresse(adresse: string): Ecran | undefined {
  const pathname = adresse.split(/[?#]/)[0] || '/'
  const candidats = ECRANS.filter((e) => correspond(e.chemin, pathname))
  const variables = (e: Ecran) => segments(e.chemin).filter((s) => s.startsWith(':')).length
  return [...candidats].sort((a, b) => variables(a) - variables(b))[0]
}
