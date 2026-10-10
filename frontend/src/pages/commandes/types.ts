/**
 * Les formes des commandes, lues dans l'OpenAPI (`types.gen.ts`, routes 152–163 du lot D3) : aucune
 * n'est recopiée à la main.
 */
import type { Schema } from '../../lib/types'

export type CommandeResume = Schema<'CommandeResume'>
export type CommandeFiche = Schema<'CommandeFiche'>
export type ApercuCommandes = Schema<'ApercuCommandes'>
export type IndicateursServeur = Schema<'IndicateursCommandes'>
export type OptionFournisseur = Schema<'OptionFournisseur'>
export type LigneCommande = Schema<'LigneCommande'>
export type Decision = Schema<'Decision'>
export type ReceptionDuBon = Schema<'ReceptionDuBon'>
export type Jalons = Schema<'Jalons'>
export type CommandeModification = Schema<'CommandeModification'>
export type ConfirmationPrix = Schema<'ConfirmationPrix'>
export type ExpeditionEntree = Schema<'ExpeditionEntree'>

/** Les gestes d'un bon, tels que la fiche les annonce (`actions` : `null` = permis, sinon la raison). */
export type Geste =
  | 'modifier'
  | 'supprimer'
  | 'envoyer'
  | 'approuver'
  | 'renvoyer'
  | 'prix'
  | 'expedition'
  | 'solder'
  | 'rouvrir'
  | 'imprimer'

/** La raison du refus d'un geste (`undefined` s'il est permis) : le bouton grisé la dit. */
export function raison(c: Pick<CommandeFiche, 'actions'>, geste: Geste): string | undefined {
  return c.actions[geste] ?? undefined
}
