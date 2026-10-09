/** Données d'essai des opérations (essais vitest du lot F6). N'est importé que par les essais. */
import type { LigneSaisie } from './saisie'
import type { LigneOperation, Motifs, OperationFiche } from './types'

export const MOTIFS: Motifs = {
  types: [
    { type: 'ouverture', libelle: 'Stock d’ouverture', roles: ['direction', 'achats'] },
    { type: 'retour_machine', libelle: 'Retour des machines', roles: ['direction', 'alimentation'] },
    {
      type: 'transfert',
      libelle: 'Transfert entre magasins',
      roles: ['direction', 'achats', 'alimentation'],
    },
    { type: 'ajustement', libelle: 'Ajustement justifié', roles: ['direction', 'achats'] },
    { type: 'retour_fournisseur', libelle: 'Retour au fournisseur', roles: ['direction', 'achats'] },
  ],
  motifs: [
    { id: 9, type: 'ajustement', libelle: 'Matière retrouvée', code_r: null, impose_role: null },
    { id: 10, type: 'ajustement', libelle: 'Perte / casse', code_r: null, impose_role: null },
    { id: 12, type: 'transfert', libelle: 'Rangement', code_r: null, impose_role: null },
    { id: 13, type: 'transfert', libelle: 'Libération de quarantaine', code_r: null, impose_role: 'achats' },
    { id: 14, type: 'transfert', libelle: 'Mise en quarantaine', code_r: null, impose_role: null },
  ],
  reclamation_motifs: [],
  reclamation_issues: [],
}

export function ligneOperationEssai(autres: Partial<LigneOperation> = {}): LigneOperation {
  return {
    id: 1,
    matiere_id: 1,
    reference: 'IMP FRISÉ ROUGE',
    designation: '',
    kg_par_ml: 0,
    lot_id: 11,
    lot: 'L24-100',
    lot_interne: false,
    magasin_id: 1,
    magasin: 'PRINCIPAL',
    magasin_destination_id: null,
    magasin_destination: '',
    quantite: 50,
    prix: null,
    devise: null,
    ...autres,
  }
}

export function operationEssai(autres: Partial<OperationFiche> = {}): OperationFiche {
  return {
    id: 5,
    numero: null,
    type: 'transfert',
    type_libelle: 'Transfert entre magasins',
    statut: 'brouillon',
    date: '2026-10-08',
    ordre_id: null,
    ordre: '',
    fournisseur_id: null,
    fournisseur: '',
    motif_id: 12,
    motif: 'Rangement',
    code_motif: '',
    commentaire: '',
    cree_par: 'Ahmed',
    cree_le: '2026-10-08T09:00:00+01:00',
    validee_par: '',
    validee_le: null,
    annulee_par: '',
    annulee_le: null,
    annulation_motif: '',
    total: 50,
    version: 2,
    peut_agir: true,
    raison: '',
    liberation: false,
    mise_en_quarantaine: false,
    lignes: [ligneOperationEssai({ magasin_destination_id: 3, magasin_destination: 'ATELIER' })],
    valeurs: null,
    blocages: [],
    ...autres,
  }
}

export function ligneSaisieEssai(autres: Partial<LigneSaisie> = {}): LigneSaisie {
  return {
    cle: 'n1',
    matiere_id: 1,
    reference: 'IMP FRISÉ ROUGE',
    kg_par_ml: 0,
    lot_id: 11,
    lot: 'L24-100',
    lot_numero: '',
    lot_interne: false,
    magasin_id: 1,
    magasin: 'PRINCIPAL',
    magasin_destination_id: 2,
    magasin_destination: 'QUAR',
    quantite: 50,
    prix: 0,
    devise: 'MAD',
    quarantaine: false,
    disponible: 420,
    fournisseur: 'LOMAT',
    ...autres,
  }
}
