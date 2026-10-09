/**
 * Les formes du plan d'achat et de la préparation, lues dans l'OpenAPI (`types.gen.ts`, routes
 * 149 et 150 du lot D3) : aucune n'est recopiée à la main.
 */
import type { Schema } from '../../lib/types'

export type PlanAchat = Schema<'PlanAchat'>
export type GroupeFournisseur = Schema<'GroupeFournisseur'>
export type LignePlan = Schema<'LignePlan'>
export type Preparation = Schema<'PreparationCommande'>
export type LignePreparation = Schema<'LignePreparation'>
export type UniteCommande = Schema<'UniteCommande'>
export type BonEnPreparation = Schema<'BonEnPreparation'>
export type CommandeCreation = Schema<'CommandeCreation'>
export type CommandeCreee = Schema<'CommandeFiche'>
export type Matiere = Schema<'MatiereResume'>
export type Devise = Schema<'DeviseFiche'>
