/**
 * Données d'essai du catalogue (vitest seulement : aucune page ne l'importe). Les formes sont
 * celles de l'OpenAPI ; chaque fabrique prend des changements.
 */
import type { Reponse } from '../../essais/monter'
import type {
  Classification,
  Fournisseur,
  Matiere,
  MatiereFiche,
  RoleNomenclature,
  UniteTitrage,
  Valeur,
} from './types'

export function roleEssai(id: number, code: string, lineaire = false, ordre = id): RoleNomenclature {
  return { id, code, lineaire, de_base: true, ordre, version: 1, nb_matieres: 0, nb_qualites: 0 }
}

export function valeurEssai(id: number, code: string, autres: Partial<Valeur> = {}): Valeur {
  return { id, code, libelle: null, commentaire: '', actif: true, version: 1, nb_matieres: 0, ...autres }
}

export function uniteEssai(
  id: number,
  code: string,
  ordre: number,
  autres: Partial<UniteTitrage> = {},
): UniteTitrage {
  const employee = (autres.nb_titrages ?? 0) > 0
  return {
    id,
    code,
    libelle: '',
    ordre,
    actif: true,
    version: 1,
    nb_titrages: 0,
    nb_matieres: 0,
    raison_garder: employee
      ? `Écrite sur ${autres.nb_titrages} titrage(s) (${autres.nb_matieres ?? 0} matière(s)) : la désactiver plutôt que la supprimer`
      : null,
    ...autres,
  }
}

export function classificationEssai(): Classification {
  return {
    compositions: [valeurEssai(1, 'PP', { libelle: 'Polypropylène', nb_matieres: 3 })],
    types_fil: [valeurEssai(2, 'FRZ', { libelle: 'Frisé' })],
    titrages: [valeurEssai(3, '2900 Dtex', { valeur: '2900', unite: 'Dtex' })],
    couleurs: [valeurEssai(4, 'Rouge'), valeurEssai(5, 'Ivoire', { actif: false })],
    roles: [roleEssai(1, 'Poil'), roleEssai(2, 'Chaîne'), roleEssai(5, 'Cuir', true)],
    unites_titrage: [
      uniteEssai(1, 'Dtex', 10, { nb_titrages: 1, nb_matieres: 3 }),
      uniteEssai(2, 'Deniers', 20),
      uniteEssai(3, 'Nm', 30),
      uniteEssai(6, 'lbs', 60),
      uniteEssai(7, 'Nec', 50, { actif: false }),
    ],
  }
}

export function matiereEssai(autres: Partial<MatiereFiche> = {}): MatiereFiche {
  return {
    id: 12,
    version: 3,
    reference: 'PP FRZ-2900 Dtex-Rouge 7001',
    designation: 'Rouge (7001)',
    role_id: 1,
    role: 'Poil',
    lineaire: false,
    composition_id: 1,
    composition: 'PP',
    composition_libelle: 'Polypropylène',
    type_fil_id: 2,
    type_fil: 'FRZ',
    titrage_id: 3,
    titrage: '2900 Dtex',
    titrage_unite: 'Dtex',
    couleur_id: 4,
    couleur: 'Rouge',
    couleur_libelle: 'Rouge',
    couleur_code: '7001',
    fournisseur_id: 7,
    fournisseur: 'Mersin Iplik',
    prix: 2.5,
    unite_prix: 'kg',
    prix_kg: 2.5,
    devise: 'USD',
    densite: 0,
    kg_par_ml: 0,
    unite_achat: 'kg',
    contenance_achat: 1,
    conditionnement: { unite: 'Palette', contenance: 240, declare: false },
    contenance_palette: 240,
    minimum_commande: 500,
    poids_bobine: 2.5,
    bobines_palette: 96,
    stock_min: 500,
    couv_min_mois: 1.5,
    groupe_equiv: 'PP-ROUGE',
    priorite_equiv: 10,
    code_douanier_id: null,
    code_douanier: null,
    actif: true,
    stock: 1107.7,
    utilisee: true,
    usages: ['des mouvements de stock', 'des recettes'],
    modifie_le: '2026-10-08T09:00:00+01:00',
    modifie_par: 'Nadia',
    ...autres,
  }
}

/** Une matière de liste (sans usages). */
export function resumeEssai(autres: Partial<Matiere> = {}): Matiere {
  const { usages: _u, modifie_le: _l, modifie_par: _p, ...resume } = matiereEssai()
  return { ...resume, ...autres }
}

export function fournisseurEssai(autres: Partial<Fournisseur> = {}): Fournisseur {
  return {
    id: 7,
    nom: 'Mersin Iplik',
    pays: 'TURKEY',
    actif: true,
    code: 'MER',
    contact: 'Ayse',
    telephone: '',
    email: 'ayse@mersin.tr',
    devise: 'USD',
    delai_jours: 60,
    couverture_commande_jours: 0,
    mode_paiement: 'Virement',
    delai_paiement_jours: 60,
    conditions_paiement: '',
    incoterm: 'FOB',
    port_chargement: 'Mersin',
    banque: '',
    notes: '',
    version: 4,
    local: false,
    devises: { USD: 34 },
    nb_matieres: 34,
    nb_commandes: 2,
    nb_receptions: 1,
    nb_lots: 1,
    nb_operations: 0,
    nb_factures: 0,
    nb_pieces: 0,
    delai_mesure_jours: 80,
    livraisons_mesurees: 4,
    utilise: true,
    empechements: ['des matières du catalogue', 'des commandes'],
    modifie_le: null,
    ...autres,
  }
}

/** Les lectures communes du catalogue, pour `fauxServeur`. */
export function reponsesCatalogue(autres: Record<string, Reponse> = {}): Record<string, Reponse> {
  return {
    'GET /matieres': {
      corps: [
        resumeEssai(),
        resumeEssai({
          id: 13,
          reference: 'CUIR NAT 40',
          role_id: 5,
          role: 'Cuir',
          lineaire: true,
          prix: 3.2,
          unite_prix: 'ml',
          prix_kg: 228.57,
          devise: 'MAD',
          densite: 0.014,
          kg_par_ml: 0.014,
          actif: false,
        }),
      ],
    },
    'GET /matieres/12': { corps: matiereEssai() },
    'GET /classification': { corps: classificationEssai() },
    'GET /fournisseurs': { corps: [fournisseurEssai()] },
    'GET /fournisseurs/7': { corps: fournisseurEssai() },
    'GET /devises': {
      corps: [
        {
          code: 'USD',
          nom: 'Dollar',
          cours: 10,
          cours_le: null,
          cours_repris: false,
          actif: true,
          version: 1,
        },
        {
          code: 'MAD',
          nom: 'Dirham',
          cours: 1,
          cours_le: null,
          cours_repris: false,
          actif: true,
          version: 1,
        },
      ],
    },
    'GET /codes-douaniers': { corps: [] },
    'GET /historique/matiere/12': { corps: [] },
    'GET /fournisseurs/performance': { statut: 404, corps: { detail: 'Introuvable.', code: 'introuvable' } },
    ...autres,
  }
}
