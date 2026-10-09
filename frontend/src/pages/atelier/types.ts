/**
 * Les formes des routes lues par l'atelier, tirées de l'OpenAPI (`types.gen.ts`). Seuls les
 * signalements (routes 221–223, lot D8) n'y sont pas encore : leur forme est PROVISOIRE, écrite
 * d'après API-PRO et MODELE-DONNEES § 3.9.2, à remplacer par `Schema<'SignalementFiche'>`.
 */
import type { Page, Schema } from '../../lib/types'

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

/** Un besoin signalé (route 221, PROVISOIRE tant que D8 ne publie pas la route). */
export interface SignalementFiche {
  id: number
  quand: string
  par_id: number
  par: string
  matiere_id: number | null
  reference?: string | null
  texte: string
  urgence: 'normale' | 'urgente'
  traite_par?: string | null
  traite_le?: string | null
  reponse?: string | null
}

export type PageSignalements = Page<SignalementFiche>
