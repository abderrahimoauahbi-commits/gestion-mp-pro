/** Données d'essai des qualités (vitest seulement : aucune page ne l'importe). */
import type { Reponse } from '../../essais/monter'
import { reponsesCatalogue, resumeEssai } from '../catalogue/donneesEssai'
import type { LigneRecette, QualiteFiche, VersionRecette } from './types'

export function ligneEssai(autres: Partial<LigneRecette> = {}): LigneRecette {
  return {
    qualite_id: 2,
    qualite: 'ATL-02',
    matiere_id: 12,
    reference: 'PP FRZ-2900 Dtex-Rouge 7001',
    role_id: 1,
    role: 'Poil',
    lineaire: false,
    nature: 'Polypropylène',
    designation: 'Rouge (7001)',
    fournisseur: 'Mersin Iplik',
    pourcentage: 100,
    kg_m2: 1.2,
    ml_m2: null,
    densite: 0,
    prix_kg: 2.5,
    prix: 2.5,
    unite_prix: 'kg',
    devise_prix: 'USD',
    cout_m2_mad: 31.5,
    ...autres,
  }
}

export function qualiteEssai(autres: Partial<QualiteFiche> = {}): QualiteFiche {
  return {
    id: 2,
    code: 'ATL-02',
    nom: 'Atlas frangé',
    actif: true,
    version: 5,
    base_mensuelle: 1200,
    saisonnalite: [1, 1, 1, 1, 1, 1.2, 1, 1, 1, 1, 1, 0.8],
    poids: [
      { role_id: 1, role: 'Poil', lineaire: false, poids: 1.2 },
      { role_id: 5, role: 'Cuir', lineaire: true, poids: 2 },
    ],
    recette: [
      ligneEssai(),
      ligneEssai({
        matiere_id: 13,
        reference: 'CUIR NAT 40',
        role_id: 5,
        role: 'Cuir',
        lineaire: true,
        kg_m2: 0.028,
        ml_m2: 2,
        densite: 0.014,
        prix_kg: 228.57,
        prix: 3.2,
        unite_prix: 'ml',
        devise_prix: 'MAD',
        cout_m2_mad: 6.72,
      }),
    ],
    controle: { roles_utilises: 2, roles_conformes: 2, ecarts: [], conforme: true },
    kg_m2: 1.228,
    cout_m2_mad: 38.22,
    fabrications: 3,
    facteurs_cout: { perte: 1.05, cours: { USD: 10, MAD: 1 } },
    avertissement: '',
    ...autres,
  }
}

export function versionEssai(id: number, autres: Partial<VersionRecette> = {}): VersionRecette {
  return {
    id,
    numero: id,
    valide_depuis: `2026-10-0${id}T09:00:00+01:00`,
    par: { id: 1, nom: 'MAZARI' },
    origine: 'saisie',
    motif: '',
    restauree_de: null,
    en_vigueur: false,
    lignes: [
      {
        matiere_id: 12,
        reference: 'PP FRZ-2900 Dtex-Rouge 7001',
        role_id: 1,
        role: 'Poil',
        pourcentage: 100,
      },
    ],
    poids: [{ role_id: 1, role: 'Poil', poids: 1.2 }],
    ...autres,
  }
}

/** Deux versions : celle en vigueur (Poil et Cuir) et une ancienne (Poil à 90/10). */
export function versionsEssai(): VersionRecette[] {
  return [
    versionEssai(3, {
      en_vigueur: true,
      lignes: [
        ...versionEssai(3).lignes,
        { matiere_id: 13, reference: 'CUIR NAT 40', role_id: 5, role: 'Cuir', pourcentage: 100 },
      ],
    }),
    versionEssai(2, {
      lignes: [
        {
          matiere_id: 12,
          reference: 'PP FRZ-2900 Dtex-Rouge 7001',
          role_id: 1,
          role: 'Poil',
          pourcentage: 90,
        },
        {
          matiere_id: 14,
          reference: 'PP FRZ-2900 Dtex-Beige 7002',
          role_id: 1,
          role: 'Poil',
          pourcentage: 10,
        },
      ],
    }),
  ]
}

export function reponsesQualites(autres: Record<string, Reponse> = {}): Record<string, Reponse> {
  const q = qualiteEssai()
  return {
    ...reponsesCatalogue({
      'GET /matieres': {
        corps: [
          resumeEssai(),
          resumeEssai({ id: 14, reference: 'PP FRZ-2900 Dtex-Beige 7002', couleur: 'Beige' }),
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
          }),
        ],
      },
    }),
    'GET /qualites': {
      corps: [
        q,
        qualiteEssai({
          id: 3,
          code: 'ESS-99',
          nom: 'Essai',
          actif: false,
          recette: [],
          controle: { roles_utilises: 0, roles_conformes: 0, ecarts: [], conforme: true },
        }),
      ],
    },
    'GET /qualites/2': { corps: q },
    'GET /nomenclature': {
      corps: {
        lignes: q.recette,
        controle: [{ ...q.controle, qualite_id: 2, qualite: 'ATL-02', actif: true }],
      },
    },
    'GET /qualites/2/versions': { corps: versionsEssai() },
    'GET /qualites/2/plan/versions': { corps: [] },
    'GET /historique/qualite/2': { corps: [] },
    ...autres,
  }
}
