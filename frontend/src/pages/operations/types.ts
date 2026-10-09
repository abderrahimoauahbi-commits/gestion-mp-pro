/**
 * Les formes des opérations de stock lues dans l'OpenAPI (routes 115–123, 241) et ce que l'écran
 * en dit : onglets, libellés des types, gestes « Nouveau … ».
 */
import type { Role } from '../../lib/types'
import type { Schema } from '../../lib/types'

export type OperationFiche = Schema<'OperationFiche'>
export type LigneOperation = Schema<'LigneOperation'>
export type PageOperations = Schema<'PageOperations'>
export type Motifs = Schema<'Motifs'>
export type MotifLu = Schema<'MotifLu'>
export type MagasinFiche = Schema<'MagasinFiche'>
export type MatiereResume = Schema<'MatiereResume'>
export type DeviseFiche = Schema<'DeviseFiche'>
export type LotSolde = Schema<'LotSolde'>
export type TypeOperation = Schema<'TypeOperation'>

export const TYPES: readonly TypeOperation[] = [
  'ouverture',
  'transfert',
  'ajustement',
  'retour_fournisseur',
  'retour_machine',
]

/** Le geste « Nouveau … » de chaque onglet. */
export const NOUVEAU: Record<TypeOperation, string> = {
  ouverture: 'Nouveau stock d’ouverture',
  transfert: 'Nouveau transfert',
  ajustement: 'Nouvel ajustement',
  retour_fournisseur: 'Nouveau retour au fournisseur',
  retour_machine: 'Nouveau retour des machines',
}

/** La note de chaque onglet (ECRANS-PRO partie 6). */
export const NOTES: Record<TypeOperation, string> = {
  ouverture:
    'Le stock réel de départ, lot par lot, avec son prix d’achat au kilo : il fixe le coût moyen. Le lot se crée à la validation.',
  transfert:
    'Déplacer un lot d’un magasin à un autre — dont la mise en quarantaine (achats, direction, alimentation) et la libération d’une quarantaine (achats, direction, après contrôle).',
  ajustement:
    'Corriger le stock d’un lot hors inventaire : perte, casse, matière retrouvée, erreur de saisie. Chaque ajustement se justifie.',
  retour_fournisseur:
    'Rendre au fournisseur une matière non conforme ou en excédent : le solde de la commande se rouvre. Un retour ne mêle pas deux fournisseurs.',
  retour_machine:
    'La matière qui revient des machines. Les retours se saisissent au téléphone (Retour des machines) ou depuis l’ordre (« Retour des machines » sur sa fiche).',
}

/** Les rôles d'un type selon `GET motifs` (la direction passe partout). */
export function rolesDuType(motifs: Motifs | undefined, type: string): readonly string[] {
  return motifs?.types.find((t) => t.type === type)?.roles ?? []
}

/** Ce rôle peut-il saisir ce type d'opération ? */
export function peutSaisir(motifs: Motifs | undefined, type: string, role: Role): boolean {
  return role === 'direction' || rolesDuType(motifs, type).includes(role)
}

/** Le libellé d'un type (« Stock d'ouverture », « Transfert entre magasins »…). */
export function libelleDuType(motifs: Motifs | undefined, type: string): string {
  return motifs?.types.find((t) => t.type === type)?.libelle ?? type
}

export const LIBERATION = 'Libération de quarantaine'
export const MISE_EN_QUARANTAINE = 'Mise en quarantaine'
export const MATIERE_RETROUVEE = 'Matière retrouvée'
