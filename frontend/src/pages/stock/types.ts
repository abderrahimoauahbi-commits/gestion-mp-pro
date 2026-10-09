/**
 * Les formes du stock, des lots, des mouvements, de la traçabilité et des brouillons, lues dans
 * l'OpenAPI (`types.gen.ts`, routes 103–123 des lots S4 et D5) : aucune n'est recopiée à la main.
 */
import type { Schema } from '../../lib/types'

export type EtatStock = Schema<'EtatStock'>
export type LigneStock = Schema<'LigneStock'>
export type FicheStockMatiere = Schema<'FicheStockMatiere'>
export type BesoinDeQualite = Schema<'BesoinDeQualite'>
export type FilSurMetier = Schema<'FilSurMetier'>
export type LotSolde = Schema<'LotSolde'>
export type LotFiche = Schema<'LotFiche'>
export type SoldeMagasin = Schema<'SoldeMagasin'>
export type MouvementLigne = Schema<'MouvementLigne'>
export type PageMouvements = Schema<'PageMouvements'>
export type Tracabilite = Schema<'Tracabilite'>
export type EtapeTracee = Schema<'EtapeTracee'>
export type Brouillons = Schema<'Brouillons'>
export type Brouillon = Schema<'Brouillon'>
export type ResultatValidationGroupee = Schema<'ResultatValidationGroupee'>
export type Magasin = Schema<'MagasinFiche'>
export type MatiereResume = Schema<'MatiereResume'>
export type Motifs = Schema<'Motifs'>
export type OperationFiche = Schema<'OperationFiche'>

/** Un magasin de quarantaine (`MagasinFiche.type`) : détenu, pas disponible. */
export const estQuarantaine = (type: string | null | undefined) =>
  (type ?? '').toLowerCase() === 'quarantaine'

/** Au-dessous du demi-gramme, une quantité est nulle (règle des lots, seuil de Gestion MP). */
export const POUSSIERE = 0.0005
