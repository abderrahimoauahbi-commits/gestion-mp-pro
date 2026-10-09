/**
 * Les formes des qualités et recettes, lues dans l'OpenAPI (`types.gen.ts`, routes 82–93 du lot
 * D2) : aucune n'est recopiée à la main.
 */
import type { Schema } from '../../lib/types'

export type Qualite = Schema<'QualiteResume'>
export type QualiteFiche = Schema<'QualiteFiche'>
export type QualiteCorps = Schema<'QualiteModification'>
export type LigneRecette = Schema<'LigneRecetteFiche'>
export type Nomenclature = Schema<'Nomenclature'>
export type ControleNomenclature = Schema<'ControleNomenclature'>
export type VersionRecette = Schema<'RecetteVersionFiche'>
export type VersionPlan = Schema<'PlanVersionFiche'>
export type FacteursCout = Schema<'FacteursCout'>
