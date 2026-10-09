/**
 * Les formes de l'inventaire lues dans l'OpenAPI (routes 124–133, 245). Ses statuts (« Comptage en
 * cours », « Validé », « Abandonné », « Annulé ») sont dans la table unique `lib/statuts.ts`.
 */
import type { Ton } from '../../lib/statuts'
import type { Schema } from '../../lib/types'

export type InventaireResume = Schema<'InventaireResume'>
export type InventaireFiche = Schema<'InventaireFiche'>
export type LigneInventaire = Schema<'LigneInventaire'>
export type DefautsInventaire = Schema<'DefautsInventaire'>
export type MatiereACompter = Schema<'MatiereACompter'>
export type MagasinFiche = Schema<'MagasinFiche'>
export type MatiereResume = Schema<'MatiereResume'>
export type LotSolde = Schema<'LotSolde'>

/** Le seuil sous lequel un écart est de la poussière (0,001 kg, comme le serveur). */
export const POUSSIERE = 0.001

/**
 * Le ton de « Hors tolérance » (règle unique des deux onglets et de la fiche, an. 23) : critique
 * s'il reste des écarts sans justification, attention s'ils sont tous justifiés, ok sinon.
 */
export function tonHorsTolerance(hors: number, sansJustification: number): Ton {
  if (sansJustification > 0) return 'critique'
  return hors > 0 ? 'attention' : 'ok'
}

/** Le magasin d'un inventaire : son code, ou « Tous les magasins ». */
export function magasinDe(i: { magasin_id: number | null; magasin: string }): string {
  return i.magasin_id == null ? 'Tous les magasins' : i.magasin
}
