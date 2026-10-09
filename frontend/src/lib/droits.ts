/**
 * Les droits d'écran, dérivés du registre (`routes.ts`) : le menu d'un rôle, la garde d'une
 * adresse, les onglets qu'il voit, son arrivée. Le serveur décide de toute façon (`droit(...)` par
 * route, ARCHITECTURE § 5.2) : l'écran ne montre que ce que le serveur acceptera.
 *
 * Pas de passe-droit implicite : la direction est nommée dans chaque écran qui lui est ouvert,
 * l'administrateur technique n'est nommé que dans les écrans techniques (Administration, Mode
 * d'emploi, Mon compte).
 */
import { ECRANS, ecranDeAdresse, entreesDuMenu, GROUPES, type Ecran, type Groupe } from '../routes'
import type { Role } from './types'

/** Le nom de chaque rôle, tel qu'il s'affiche (menu du compte, visages, « réservé : … »). */
export const LIBELLES_ROLES: Record<Role, string> = {
  direction: 'Direction',
  achats: 'Achats',
  alimentation: 'Alimentation des machines',
  administrateur: 'Administrateur technique',
}

/** Les rôles métier (C) : ceux qui voient des données de l'usine (recherche globale, besoins). */
export const ROLES_METIER: readonly Role[] = ['direction', 'achats', 'alimentation']

/** Un téléphone : écran étroit **et** tactile (ECRANS-PRO, coque : « étroit et tactile »). */
export const REQUETE_TELEPHONE = '(max-width: 700px) and (pointer: coarse)'

export function estTelephone(): boolean {
  return typeof window.matchMedia === 'function' && window.matchMedia(REQUETE_TELEPHONE).matches
}

/**
 * L'arrivée d'un rôle (ARCHITECTURE § 10.1) : direction → Cockpit ; achats → Ma journée ;
 * alimentation → atelier au téléphone, Ma journée au bureau ; administrateur → Administration.
 */
export function accueilDe(role: Role, telephone = estTelephone()): string {
  if (role === 'direction') return '/cockpit'
  if (role === 'administrateur') return '/administration'
  if (role === 'alimentation' && telephone) return '/atelier'
  return '/accueil'
}

/** Les onglets d'un écran que ce rôle voit (le premier est l'onglet par défaut). */
export function ongletsPermis(ecran: Ecran, role: Role) {
  return (ecran.onglets ?? []).filter((o) => !o.roles || o.roles.includes(role))
}

/** Pourquoi une adresse est refusée à ce rôle : inconnue, réservée, ou `null` si elle est permise. */
export function refus(role: Role, adresse: string): 'inconnue' | 'reservee' | null {
  const ecran = ecranDeAdresse(adresse)
  if (!ecran) return 'inconnue'
  if (!ecran.roles.includes(role)) return 'reservee'
  const onglet = new URLSearchParams(adresse.split('?')[1]?.split('#')[0] ?? '').get('onglet')
  if (onglet && ecran.onglets) {
    const o = ecran.onglets.find((x) => x.cle === onglet)
    if (o?.roles && !o.roles.includes(role)) return 'reservee'
  }
  return null
}

/** Vrai si ce rôle peut ouvrir cette adresse (écran déclaré, rôle permis, onglet permis). */
export function permis(role: Role, adresse: string): boolean {
  return refus(role, adresse) === null
}

/** Les rôles qui ouvrent l'écran d'une adresse, en toutes lettres (« Direction, Achats »). */
export function rolesDe(adresse: string): string {
  const ecran = ecranDeAdresse(adresse)
  return ecran ? ecran.roles.map((r) => LIBELLES_ROLES[r]).join(', ') : ''
}

export interface GroupeDuMenu {
  groupe: Groupe
  entrees: Ecran[]
}

/** Le menu d'un rôle : ses entrées, groupe par groupe ; un groupe vide est masqué. */
export function menuDe(role: Role): GroupeDuMenu[] {
  const entrees = entreesDuMenu().filter((e) => e.roles.includes(role))
  return GROUPES.map((groupe) => ({ groupe, entrees: entrees.filter((e) => e.groupe === groupe) })).filter(
    (g) => g.entrees.length > 0,
  )
}

/** L'adresse de retour après connexion : gardée si elle est sûre et permise, sinon l'arrivée du rôle. */
export function destinationApresConnexion(role: Role, retour: string | null, telephone = estTelephone()) {
  const sure =
    retour && retour.startsWith('/') && !retour.startsWith('//') && !retour.startsWith('/connexion')
  if (sure && retour !== '/' && permis(role, retour)) return retour
  return accueilDe(role, telephone)
}

/** Tous les écrans ouverts à ce rôle (essais, recette). */
export function ecransDe(role: Role): Ecran[] {
  return ECRANS.filter((e) => e.roles.includes(role))
}
