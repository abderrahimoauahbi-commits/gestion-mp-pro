/**
 * Données d'essai de l'inventaire (essais vitest du lot F6) : une fiche, des lignes, des défauts,
 * conformes aux schémas de l'OpenAPI. N'est importé que par les essais.
 */
import type {
  DefautsInventaire,
  InventaireFiche,
  InventaireResume,
  LigneInventaire,
  LotSolde,
  MagasinFiche,
  MatiereResume,
} from './types'

export function ligneEssai(autres: Partial<LigneInventaire> = {}): LigneInventaire {
  return {
    id: 1,
    lot_id: 11,
    lot: 'L24-100',
    lot_interne: false,
    lot_trouve: false,
    matiere_id: 1,
    reference: 'IMP FRISÉ ROUGE',
    designation: '',
    kg_par_ml: 0,
    poids_bobine: 2.5,
    bobines_palette: 24,
    magasin_id: 1,
    magasin: 'PRINCIPAL',
    theorique: 420,
    compte: null,
    palettes: null,
    bobines: null,
    compte_par: '',
    second_compte: null,
    second_par: '',
    quatre_yeux: '',
    retenu: null,
    ecart: null,
    ecart_pourcent: null,
    cmup_mad: 30,
    valeur_ecart_mad: null,
    hors_tolerance: false,
    a_recompter: false,
    justification: '',
    ...autres,
  }
}

export function resumeEssai(autres: Partial<InventaireResume> = {}): InventaireResume {
  return {
    id: 7,
    numero: 'INV-2026-0007',
    libelle: 'Inventaire de tout le stock PRINCIPAL',
    statut: 'ouvert',
    date: '2026-10-08',
    magasin_id: 1,
    magasin: 'PRINCIPAL',
    tolerance: 0.02,
    perimetre: 'Tout le stock',
    criteres: { matieres: [], roles: [], compositions: [], classes_abc: [] },
    nb_matieres_suspendues: 5,
    cree_par: 'Karim BENALI',
    cree_le: '2026-10-08T09:00:00+01:00',
    valide_par: '',
    valide_le: null,
    abandonne_par: '',
    abandonne_le: null,
    annule_par: '',
    annule_le: null,
    annulation_motif: '',
    abandon_motif: '',
    nb_lignes: 2,
    nb_comptees: 0,
    hors_tolerance: 0,
    sans_justification: 0,
    a_recompter: 0,
    recomptees: 0,
    recomptes_meme_personne: 0,
    ecart_total: 0,
    ecart_absolu: 0,
    ecart_valeur_mad: 0,
    ecart_valeur_absolue_mad: 0,
    version: 3,
    ...autres,
  }
}

export function ficheEssai(autres: Partial<InventaireFiche> = {}): InventaireFiche {
  return {
    ...resumeEssai(),
    blocages: ['Aucun lot compté : saisir les comptages avant de valider.'],
    lignes: [ligneEssai(), ligneEssai({ id: 2, lot_id: 12, lot: 'L24-101', theorique: 260 })],
    ...autres,
  }
}

export const DEFAUTS: DefautsInventaire = {
  tolerance: 0.02,
  roles: [
    { id: 1, code: 'Poil' },
    { id: 2, code: 'Chaîne' },
  ],
  compositions: [{ id: 4, code: 'Coton' }],
  cadence_jours: { A: 30, B: 90, C: 365 },
}

export const MAGASINS: MagasinFiche[] = [
  {
    id: 1,
    code: 'PRINCIPAL',
    nom: 'Magasin principal',
    type: 'stock_courant',
    contenu: '',
    actif: true,
    kg_detenus: 680,
    version: 1,
  },
  {
    id: 2,
    code: 'QUAR',
    nom: 'Quarantaine',
    type: 'quarantaine',
    contenu: '',
    actif: true,
    kg_detenus: 95,
    version: 1,
  },
]

export function matiereEssai(autres: Partial<MatiereResume> = {}): MatiereResume {
  const base: MatiereResume = {
    id: 1,
    version: 1,
    reference: 'IMP FRISÉ ROUGE',
    designation: '',
    role_id: 1,
    role: 'Poil',
    lineaire: false,
    composition_id: null,
    composition: null,
    composition_libelle: null,
    type_fil_id: null,
    type_fil: null,
    titrage_id: null,
    titrage: null,
    titrage_unite: null,
    couleur_id: null,
    couleur: null,
    couleur_libelle: null,
    couleur_code: '',
    fournisseur_id: 1,
    fournisseur: 'LOMAT',
    prix: 3.2,
    unite_prix: 'kg',
    prix_kg: 3.2,
    devise: 'EUR',
    densite: 0,
    kg_par_ml: 0,
    unite_achat: 'kg',
    contenance_achat: 1,
    conditionnement: { unite: 'bobine', contenance: 2.5, declare: false },
    contenance_palette: 0,
    minimum_commande: 0,
    poids_bobine: 2.5,
    bobines_palette: 24,
    stock_min: 0,
    couv_min_mois: 0,
    groupe_equiv: '',
    priorite_equiv: null,
    code_douanier_id: null,
    code_douanier: null,
    actif: true,
    stock: 680,
    utilisee: true,
  }
  return { ...base, ...autres }
}

export function lotEssai(autres: Partial<LotSolde> = {}): LotSolde {
  return {
    lot_id: 11,
    lot: 'L24-100',
    interne: false,
    matiere_id: 1,
    reference: 'IMP FRISÉ ROUGE',
    designation: '',
    role: 'Poil',
    kg_par_ml: 0,
    fournisseur: 'LOMAT',
    entre_le: '2026-08-01',
    poids_bobine: 2.5,
    bobines_palette: 24,
    quantite: 420,
    disponible: 420,
    quarantaine: 0,
    magasins: [{ magasin_id: 1, magasin: 'PRINCIPAL', type: 'stock_courant', quantite: 420 }],
    bobines: 168,
    statut: 'disponible',
    historique: { entre: 420, sorti: 0, dernier_mouvement: '2026-08-01', ordres: [] },
    ...autres,
  }
}
