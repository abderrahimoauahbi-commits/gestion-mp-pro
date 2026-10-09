/**
 * Les formes des routes lues par l'atelier, tirées de l'OpenAPI (`types.gen.ts`).
 */
import type { Schema } from '../../lib/types'

export type OrdreResume = Schema<'OrdreResume'>
export type OrdreFiche = Schema<'OrdreFiche'>
export type LigneOrdre = Schema<'LigneOrdre'>
export type Proposition = Schema<'Proposition'>
export type LigneProposee = Schema<'LigneProposee'>
export type LotPropose = Schema<'LotPropose'>
export type LotSorti = Schema<'LotSorti'>
export type LotSolde = Schema<'LotSolde'>
export type LotFiche = Schema<'LotFiche'>
export type MouvementLigne = Schema<'MouvementLigne'>
export type MagasinFiche = Schema<'MagasinFiche'>
export type Motifs = Schema<'Motifs'>
export type MotifLu = Schema<'MotifLu'>
export type MetierFiche = Schema<'MetierFiche'>
export type FilMonteFiche = Schema<'FilMonteFiche'>
export type EtageFiche = Schema<'EtageFiche'>
export type MatiereMontage = Schema<'MatiereMontage'>
export type ResultatMontage = Schema<'ResultatMontage'>
export type QualiteResume = Schema<'QualiteResume'>
export type MatiereResume = Schema<'MatiereResume'>
export type OperationFiche = Schema<'OperationFiche'>

/** Un besoin signalé (routes 221–223, lot D8). */
export type SignalementFiche = Schema<'SignalementFiche'>
export type PageSignalements = Schema<'PageSignalements'>
export type SignalementCreation = Schema<'SignalementCreation'>
