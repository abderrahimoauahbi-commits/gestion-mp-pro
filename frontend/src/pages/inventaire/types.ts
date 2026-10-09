/**
 * Les formes de l'inventaire lues dans l'OpenAPI (routes 124–133, 245) et la table de ses statuts.
 *
 * `lib/statuts.ts` (E0) ne connaît pas encore « Annulé » ni le libellé « Comptage en cours » de
 * ECRANS-PRO partie 6 : la table de l'écran est ici, une seule fois, et le badge passe par
 * `Badge({ton})`.
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

export type StatutInventaire = 'ouvert' | 'valide' | 'abandonne' | 'annule'

/** Le libellé et le ton de chaque statut (« Comptage en cours » attention, « Validé » ok…). */
export const STATUTS_INVENTAIRE: Readonly<Record<string, { libelle: string; ton: Ton }>> = {
  ouvert: { libelle: 'Comptage en cours', ton: 'attention' },
  valide: { libelle: 'Validé', ton: 'ok' },
  abandonne: { libelle: 'Abandonné', ton: 'neutre' },
  annule: { libelle: 'Annulé', ton: 'neutre' },
}

/** Le libellé et le ton d'un statut reçu (un statut inconnu se dit tel quel, en neutre). */
export function statutInventaire(statut: string): { libelle: string; ton: Ton } {
  return STATUTS_INVENTAIRE[statut] ?? { libelle: statut, ton: 'neutre' }
}

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
