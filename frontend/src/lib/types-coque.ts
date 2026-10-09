/**
 * Les formes des routes de la coque (API-PRO routes 2, 3, 8–14, 19–22, 53–56), lues dans
 * `types.gen.ts` (généré depuis l'OpenAPI du serveur, lot S2). Seul ajout : le rôle, une chaîne
 * dans l'OpenAPI, est l'un des quatre rôles de l'énumération `Role` (MODELE-DONNEES § 2).
 */
import type { Role, Schema } from './types'

export type EtatInstallation = Schema<'EtatInstallation'>
export type Installation = Schema<'Installation'>
export type Connexion = Schema<'Connexion'>
export type MoiModification = Schema<'MoiModification'>
export type ChangementCode = Schema<'ChangementCode'>
export type AppareilFiche = Schema<'AppareilFiche'>
export type Notification = Schema<'Notification'>
export type PageNotifications = Schema<'PageNotifications'>
export type ResultatRecherche = Schema<'ResultatRecherche'>
export type InventaireOuvert = Schema<'InventaireOuvert'>

/** Un nom à toucher à la connexion (poste local ou appareil enrôlé seulement). */
export type Visage = Omit<Schema<'Visage'>, 'role'> & { role: Role }

/** Le compte connecté. */
export type Moi = Omit<Schema<'Moi'>, 'role'> & { role: Role }

/** Le contexte de démarrage (GET /contexte). */
export type Contexte = Omit<Schema<'Contexte'>, 'moi'> & { moi: Moi }

/** Les compteurs des pastilles du menu, par nom (`alerte_rouge`, `anomalies`…). */
export type CompteursMenu = Contexte['compteurs']
