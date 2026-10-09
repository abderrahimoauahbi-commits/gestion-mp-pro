/**
 * Les formes des importations lues dans l'OpenAPI (routes 187–208 du lot D7, 34–41 du lot D1), et
 * les petites règles d'écran partagées par la liste, la fiche et l'analyse.
 */
import type { Ton } from '../../lib/statuts'
import type { Schema } from '../../lib/types'

export type DossierResume = Schema<'DossierResume'>
export type DossierFiche = Schema<'DossierFiche'>
export type LigneDossier = Schema<'LigneDossier'>
export type FraisDossier = Schema<'FraisDossier'>
export type Echeance = Schema<'Echeance'>
export type EnAttente = Schema<'EnAttente'>
export type FactureARattacher = Schema<'FactureARattacher'>
export type ReceptionSansFacture = Schema<'ReceptionSansFacture'>
export type ValeurDevise = Schema<'gestion_mp_pro__api__importations__schemas_fiche__ValeurDevise'>
export type Famille = Schema<'Famille'>
export type ActionsDossier = Schema<'Actions'>
export type PosteFiche = Schema<'PosteFiche'>
export type CodeDouanier = Schema<'CodeDouanierFiche'>
export type MatiereResume = Schema<'MatiereResume'>
export type FournisseurResume = Schema<'FournisseurResume'>
export type DeviseFiche = Schema<'DeviseFiche'>

/** Les onglets de la page et la liste à montrer sous une fiche. */
export const ONGLETS_PAGE = ['ouverts', 'clos', 'rattacher'] as const
export type OngletPage = (typeof ONGLETS_PAGE)[number]

/** Les volets de la fiche d'un dossier (`/dossiers/:id?onglet=`). */
export const VOLETS = [
  'familles',
  'marchandises',
  'frais',
  'echeancier',
  'pieces',
  'facture',
  'main',
  'historique',
] as const
export type Volet = (typeof VOLETS)[number]

/** « Ouvert », « Clos le 08/10/2026 14:05 », « Annulé le … » : le badge d'un dossier. */
export function statutDossier(d: Pick<DossierResume, 'statut'>): { libelle: string; ton: Ton } {
  if (d.statut === 'clos') return { libelle: 'Clos', ton: 'ok' }
  if (d.statut === 'annule') return { libelle: 'Annulé', ton: 'neutre' }
  return { libelle: 'Ouvert', ton: 'attention' }
}

/** Le seuil sous lequel des frais non répartis ne comptent pas (comme le serveur, I15). */
export const SEUIL_NON_REPARTIS = 0.005

/** Les frais (hors TVA et TVA) qu'aucune marchandise ne porte. */
export const nonRepartis = (d: Pick<DossierResume, 'charges_non_reparties_mad' | 'tva_non_repartie_mad'>) =>
  (Math.abs(d.charges_non_reparties_mad) > SEUIL_NON_REPARTIS ? d.charges_non_reparties_mad : 0) +
  (Math.abs(d.tva_non_repartie_mad) > SEUIL_NON_REPARTIS ? d.tva_non_repartie_mad : 0)

/** La part des charges dans l'achat (`null` sans achat). */
export const partCharges = (charges: number, achat: number) => (achat ? charges / achat : null)

/** « 01/26 » : le numéro, ou « Brouillon » n'existe pas ici (un dossier est numéroté dès l'ouverture). */
export const titreDossier = (d: Pick<DossierResume, 'numero' | 'libelle'>) =>
  d.libelle ? `Dossier ${d.numero} — ${d.libelle}` : `Dossier ${d.numero}`
