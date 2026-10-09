/**
 * Les formes des réceptions, réclamations, pesées et bobines, lues dans l'OpenAPI (`types.gen.ts`,
 * routes 167–186 du lot D4) : aucune n'est recopiée à la main.
 */
import type { Schema } from '../../lib/types'

export type ReceptionResume = Schema<'ReceptionResume'>
export type PageReceptions = Schema<'PageReceptions'>
export type ApercuReceptions = Schema<'ApercuReceptions'>
export type ReceptionFiche = Schema<'ReceptionFiche'>
export type LigneReception = Schema<'LigneReception'>
export type ReceptionCreation = Schema<'ReceptionCreation'>
export type ReceptionModification = Schema<'ReceptionModification'>
export type LigneReceptionEntree = Schema<'LigneReceptionEntree'>
export type FactureEntree = Schema<'FactureEntree'>
export type FactureCorrection = Schema<'FactureCorrection'>
export type Qualite = Schema<'QualiteReception'>
export type ReclamationResume = Schema<'ReclamationResume'>
export type ReclamationFiche = Schema<'ReclamationFiche'>
export type ReclamationCreation = Schema<'ReclamationCreation'>
export type PagePesees = Schema<'PagePesees'>
export type Pesee = Schema<'Pesee'>
export type EvolutionBobines = Schema<'EvolutionBobines'>
export type EvolutionBobine = Schema<'EvolutionBobine'>
export type Mesure = Schema<'Mesure'>
export type Motifs = Schema<'Motifs'>
export type Magasin = Schema<'MagasinFiche'>
export type Fournisseur = Schema<'FournisseurFiche'>
export type Reglage = Schema<'Reglage'>

/** Les gestes d'une réception, tels que la fiche les annonce (`actions` : `null` = permis, sinon la raison). */
export type GesteReception =
  'modifier' | 'supprimer' | 'valider' | 'annuler' | 'facture' | 'reclamer' | 'etiquettes'

export function raisonReception(
  r: Pick<ReceptionFiche, 'actions'>,
  geste: GesteReception,
): string | undefined {
  return r.actions[geste] ?? undefined
}
