/**
 * Les formes des réponses lues par l'Analyse (lot F8), tirées de l'OpenAPI (`types.gen.ts`) :
 * routes 210–215, 228–229, 233, 235 (D8) et la consommation des ordres (D6).
 */
import type { Schema } from '../../lib/types'

export type Valorisation = Schema<'Valorisation'>
export type LigneValorisation = Schema<'LigneValorisation'>
export type HistoriquePrix = Schema<'HistoriquePrix'>
export type PrixPaye = Schema<'PrixPaye'>
export type MatricePrix = Schema<'MatricePrix'>
export type LigneMatrice = Schema<'LigneMatrice'>
export type Opportunites = Schema<'Opportunites'>
export type OpportuniteLigne = Schema<'OpportuniteLigne'>
export type PerformanceFournisseurs = Schema<'PerformanceFournisseurs'>
export type ScoreFournisseur = Schema<'ScoreFournisseur'>
export type ReceptionNotee = Schema<'ReceptionNotee'>
export type Echeancier = Schema<'Echeancier'>
export type EcheanceLigne = Schema<'EcheanceLigne'>
export type Paiement = Schema<'Paiement'>
export type Controles = Schema<'Controles'>
export type ControleResume = Schema<'ControleResume'>
export type ColonneControle = Schema<'ColonneControle'>
export type PageControle = Schema<'PageControle'>
export type ControleSoldes = Schema<'ControleSoldes'>
export type ConsommationOrdre = Schema<'ConsommationOrdre'>
export type ParMatiere = Schema<'ParMatiere'>

/** Une ligne de contrôle : des colonnes nommées par le serveur, et les ids des fiches qu'elle cite. */
export type LigneControle = Record<string, unknown>
