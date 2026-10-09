/**
 * Données d'essai de l'analyse du coût de revient, conformes au schéma (formes prises d'une vraie
 * réponse du serveur : `GET analyse/revient`, `GET analyse/revient/qualites/{id}`, `GET matieres`,
 * `GET classification`, `GET qualites`).
 */
import type { Schema } from '../../../lib/types'
import type { Analyse, Groupe } from './colonnes'
import type { CoutQualite } from './colonnesQualite'
import type { Classification, Matiere } from './criteres'

type Ligne = Schema<'LigneDetailRevient'>
type Qualite = Schema<'QualiteResume'>

export function matiereEssai(autres: Partial<Matiere> = {}): Matiere {
  return {
    id: 2,
    version: 1,
    reference: 'IMP PES ROUGE-1500',
    designation: '',
    role_id: 1,
    role: 'Poil',
    lineaire: false,
    composition_id: 1,
    composition: 'PES',
    composition_libelle: 'Polyester',
    type_fil_id: 1,
    type_fil: 'FRI',
    titrage_id: 1,
    titrage: 'T1500',
    titrage_unite: 'den',
    couleur_id: 1,
    couleur: 'RGE',
    couleur_libelle: 'ROUGE',
    couleur_code: '',
    fournisseur_id: 1,
    fournisseur: 'Filature Bursa',
    prix: 2.8,
    unite_prix: 'kg',
    prix_kg: 2.8,
    devise: 'USD',
    densite: 0,
    kg_par_ml: 0,
    unite_achat: 'kg',
    contenance_achat: 1,
    conditionnement: { unite: 'kg', contenance: 1, declare: false },
    contenance_palette: 0,
    minimum_commande: 0,
    poids_bobine: 2.5,
    bobines_palette: 0,
    stock_min: 0,
    couv_min_mois: 0,
    groupe_equiv: '',
    priorite_equiv: null,
    code_douanier_id: 1,
    code_douanier: '5402.47.00.00',
    actif: true,
    stock: 800,
    utilisee: true,
    ...autres,
  }
}

export const MATIERES: Matiere[] = [
  matiereEssai(),
  matiereEssai({
    id: 5,
    reference: 'IMP PP NOIR-1800',
    composition_id: 2,
    composition: 'PP',
    composition_libelle: 'Polypropylène',
    titrage_id: 2,
    titrage: 'T1800',
    couleur_libelle: 'NOIR',
    couleur: 'NR',
    fournisseur: 'Beaulieu Yarns',
  }),
  matiereEssai({ id: 7, reference: 'IMP PES BLEU-1500', couleur_libelle: 'BLEU', couleur: 'BL' }),
]

function valeur(id: number, code: string, valeurTitrage: string | null = null) {
  return {
    id,
    code,
    libelle: code,
    famille: null,
    composition_detaillee: null,
    valeur: valeurTitrage,
    unite: valeurTitrage ? 'den' : null,
    commentaire: '',
    actif: true,
    version: 1,
    nb_matieres: 1,
  }
}

export const CLASSIFICATION: Classification = {
  compositions: [valeur(1, 'PES'), valeur(2, 'PP')],
  types_fil: [valeur(1, 'FRI')],
  titrages: [valeur(1, 'T1500', '1500'), valeur(2, 'T1800', '1800')],
  couleurs: [valeur(1, 'RGE')],
  roles: [],
}

export function qualiteEssai(autres: Partial<Qualite> = {}): Qualite {
  return {
    id: 3,
    code: 'Q12',
    nom: 'Shaggy rouge',
    actif: true,
    version: 1,
    base_mensuelle: 0,
    saisonnalite: [],
    poids: [],
    recette: [],
    controle: { roles_utilises: 0, roles_conformes: 0, ecarts: [], conforme: true },
    kg_m2: 2.4,
    cout_m2_mad: null,
    fabrications: 0,
    facteurs_cout: { perte: 0, cours: null },
    ...autres,
  }
}

export function groupeEssai(autres: Partial<Groupe> = {}): Groupe {
  return {
    valeur: '1500 den',
    quantite: 900,
    unites: ['kg'],
    poids: 900,
    marchandise_mad: 34272,
    charges_mad: 7300,
    tva_mad: 0,
    lignes: 1,
    dossiers: ['01/26'],
    detail: { FRET: 4200, DD: 3100 },
    unite: 'kg',
    revient_mad: 41572,
    decaisse_mad: 41572,
    marchandise_unite: 38.08,
    revient_unite: 46.19,
    marchandise_kg: 38.08,
    revient_kg: 46.19,
    surcout: 0.213,
    role: null,
    part_recette: null,
    poids_m2: null,
    cout_m2: null,
    ...autres,
  }
}

export function ligneEssai(autres: Partial<Ligne> = {}): Ligne {
  return {
    dossier: '01/26',
    date_arrivee: '2026-03-02',
    statut: 'Ouvert',
    reference: 'IMP PES ROUGE-1500',
    lot_fournisseur: 'L-BUR-18',
    fournisseur: 'Filature Bursa',
    composition: 'PES',
    type_fil: 'FRI',
    titrage: '1500 den',
    couleur: 'ROUGE',
    role_bom: 'Poil',
    quantite: 900,
    unite: 'kg',
    poids: 900,
    marchandise_mad: 34272,
    charges_mad: 7300,
    revient_mad: 41572,
    tva_mad: 0,
    decaisse_mad: 41572,
    valeur_unite: 38.08,
    revient_unite: 46.19,
    revient_kg: 46.19,
    surcout: 0.213,
    ...autres,
  }
}

export function analyseEssai(autres: Partial<Analyse> = {}): Analyse {
  return {
    axe: 'titrage',
    ids_dossiers: { '01/26': 11, '02/26': 12, '03/26': 13 },
    frais_non_repartis_mad: 0,
    dossiers_non_repartis: [],
    libelle_axe: 'Titrage',
    lignes: [
      groupeEssai(),
      groupeEssai({ valeur: '1800 den', dossiers: ['02/26', '03/26'], revient_mad: 20000, lignes: 2 }),
    ],
    detail_lignes: [],
    total_lignes: 3,
    total_poids: 1800,
    total_marchandise_mad: 68544,
    total_charges_mad: 14600,
    total_revient_mad: 61572,
    total_tva_mad: 0,
    total_decaisse_mad: 61572,
    ...autres,
  }
}

export function coutQualiteEssai(autres: Partial<CoutQualite> = {}): CoutQualite {
  return {
    ...analyseEssai({
      axe: 'reference',
      libelle_axe: 'Référence',
      lignes: [groupeEssai({ valeur: 'IMP PES ROUGE-1500', role: 'Poil', part_recette: 100, poids_m2: 2.4 })],
    }),
    qualite: 'Q12',
    nom: 'Shaggy rouge',
    references_de_la_recette: 2,
    references_importees: 1,
    roles: [
      { role: 'Poil', poids_m2: 2.4, lineaire: false, connu_m2: 2.4, cout_m2: 110.86, fils: 1, importes: 1 },
      { role: 'Trame', poids_m2: 0.6, lineaire: false, connu_m2: 0, cout_m2: 0, fils: 1, importes: 0 },
    ],
    poids_m2: 3,
    couverture: 0.8,
    cout_m2: 110.86,
    cout_m2_estime: 110.86,
    cout_kg_tapis: 46.19,
    roles_sans_cout: ['Trame'],
    ...autres,
  }
}
