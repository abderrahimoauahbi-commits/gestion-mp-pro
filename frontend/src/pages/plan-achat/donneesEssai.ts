/**
 * Données d'essai du plan d'achat et de la préparation (vitest seulement : aucune page ne
 * l'importe), relevées sur le vrai serveur (base d'essai du lot F4) ; chaque fabrique prend des
 * changements.
 */
import type { GroupeFournisseur, LignePlan, LignePreparation, PlanAchat, Preparation } from './types'

const PLAN: PlanAchat = {
  date_reference: '2026-10-09',
  indicateurs: {
    references_a_commander: 3,
    references_en_alerte: 3,
    budget_mad: 259103.430875576,
    quantite_totale: 13470.815668202766,
    references_classe_a: 1,
    ruptures: 1,
    critiques: 2,
    urgents: 0,
    attentions: 0,
    ok: 3,
    tiers: { '🔥 TIER 1': 3 },
  },
  fournisseurs: [
    {
      fournisseur_id: 3,
      fournisseur: 'Filature du Souss',
      pays: 'MAROC',
      devise_par_defaut: 'MAD',
      devises: ['MAD'],
      delai_jours: 10.0,
      contact: 'M. Filature',
      nb_references: 2,
      quantite: 7838.815668202765,
      montants_par_devise: { MAD: 143647.43087557604 },
      montant_mad: 143647.43087557604,
      part_budget: 0.5544018864982029,
      urgence: '🚨 BC URGENT',
      ruptures: 0,
      critiques: 2,
      urgents: 0,
    },
    {
      fournisseur_id: 2,
      fournisseur: 'Polyfil Industries',
      pays: 'TURQUIE',
      devise_par_defaut: 'USD',
      devises: ['USD'],
      delai_jours: 60.0,
      contact: 'M. Polyfil',
      nb_references: 1,
      quantite: 5632.0,
      montants_par_devise: { USD: 11545.599999999999 },
      montant_mad: 115455.99999999999,
      part_budget: 0.4455981135017972,
      urgence: '🚨 BC URGENT',
      ruptures: 1,
      critiques: 0,
      urgents: 0,
    },
  ],
  lignes: [
    {
      matiere_id: 5,
      fournisseur_id: 3,
      reference: 'COTON TRAME 8/2 Écru',
      nature: '',
      designation: 'Écru',
      fournisseur: 'Filature du Souss',
      classe_abc: 'A',
      statut: 'CRITIQUE',
      quantite: 3198.8156682027648,
      unite_achat: 'kg',
      quantite_achat: 3198.8156682027648,
      unite_commande: 'kg',
      unites_commande: 3198.8156682027648,
      contenance_commande: 1.0,
      prix: 27.5,
      devise: 'MAD',
      montant_devise: 87967.43087557603,
      montant_mad: 87967.43087557603,
      palettes: 0.0,
      tier: '🔥 TIER 1',
      risque: '❓ Hors catalogue',
      action: 'Émettre cette semaine',
      relance: 'CRITIQUE — COTON TRAME 8/2 Écru (Filature du Souss) — Qté: 3199 kg — 87967 MAD — Délai: 10j',
      en_preparation: 0.0,
      bons_en_preparation: [],
      stock_disponible: 978.0,
      stock_net: 978.0,
      stock_projete: 1088.7096774193549,
      commande_kg: 522.0,
      couverture_jours: 25.616698292220114,
      conso_mensuelle: 1275.0,
      kg_par_ml: 0.0,
      unites_possibles: [{ unite: 'kg', contenance: 1.0 }],
    },
    {
      matiere_id: 4,
      fournisseur_id: 2,
      reference: 'PES TWS 1800 Noir 9005',
      nature: '',
      designation: 'Noir (9005)',
      fournisseur: 'Polyfil Industries',
      classe_abc: 'B',
      statut: 'RUPTURE',
      quantite: 5632.0,
      unite_achat: 'kg',
      quantite_achat: 5632.0,
      unite_commande: 'Palette',
      unites_commande: 22.0,
      contenance_commande: 256.0,
      prix: 2.05,
      devise: 'USD',
      montant_devise: 11545.599999999999,
      montant_mad: 115455.99999999999,
      palettes: 22.0,
      tier: '🔥 TIER 1',
      risque: '❓ Hors catalogue',
      action: 'Émettre cette semaine',
      relance:
        'RUPTURE — PES TWS 1800 Noir 9005 (Polyfil Industries) — Qté: 5632 kg — 11546 USD — Délai: 60j',
      en_preparation: 0.0,
      bons_en_preparation: [],
      stock_disponible: 0.0,
      stock_net: 0.0,
      stock_projete: -1239.8387096774195,
      commande_kg: 1280.0,
      couverture_jours: -29.172675521821635,
      conso_mensuelle: 1275.0,
      kg_par_ml: 0.0,
      unites_possibles: [
        { unite: 'kg', contenance: 1.0 },
        { unite: 'Bobine', contenance: 3.2 },
        { unite: 'Palette', contenance: 256.0 },
      ],
    },
    {
      matiere_id: 6,
      fournisseur_id: 3,
      reference: 'JUTE TRAME Naturel',
      nature: '',
      designation: 'Naturel',
      fournisseur: 'Filature du Souss',
      classe_abc: 'C',
      statut: 'CRITIQUE',
      quantite: 4640.0,
      unite_achat: 'kg',
      quantite_achat: 4640.0,
      unite_commande: 'Bobine',
      unites_commande: 928.0,
      contenance_commande: 5.0,
      prix: 12.0,
      devise: 'MAD',
      montant_devise: 55680.0,
      montant_mad: 55680.0,
      palettes: 0.0,
      tier: '🔥 TIER 1',
      risque: '❓ Hors catalogue',
      action: 'Émettre cette semaine',
      relance: 'CRITIQUE — JUTE TRAME Naturel (Filature du Souss) — Qté: 4640 kg — 55680 MAD — Délai: 10j',
      en_preparation: 0.0,
      bons_en_preparation: [],
      stock_disponible: 0.0,
      stock_net: 505.0,
      stock_projete: 506.4516129032258,
      commande_kg: 1000.0,
      couverture_jours: 9.930423782416192,
      conso_mensuelle: 1530.0,
      kg_par_ml: 0.0,
      unites_possibles: [
        { unite: 'kg', contenance: 1.0 },
        { unite: 'Bobine', contenance: 5.0 },
      ],
    },
  ],
}

const PREPARATION: Preparation = {
  fournisseur_id: 2,
  fournisseur: 'Polyfil Industries',
  pays: 'TURQUIE',
  contact: 'M. Polyfil',
  email: 'achats@polyfil.com',
  delai_jours: 60.0,
  devise_par_defaut: 'USD',
  date_reference: '2026-10-09',
  lignes: [
    {
      matiere_id: 4,
      reference: 'PES TWS 1800 Noir 9005',
      nature: '',
      designation: 'Noir (9005)',
      statut: 'RUPTURE',
      classe_abc: 'B',
      kg_par_ml: 0.0,
      stock_projete: -1239.8387096774195,
      conso_mensuelle: 1275.0,
      couverture_jours: -29.172675521821635,
      quantite_suggeree: 5632.0,
      palettes_suggerees: 22.0,
      contenance_palette: 256.0,
      unite_commande: 'Palette',
      contenance_commande: 256.0,
      unites_suggerees: 22.0,
      unites_possibles: [
        { unite: 'kg', contenance: 1.0 },
        { unite: 'Bobine', contenance: 3.2 },
        { unite: 'Palette', contenance: 256.0 },
      ],
      minimum_commande: 0.0,
      prix_indicatif: 2.05,
      devise: 'USD',
      montant_indicatif_mad: 115455.99999999999,
      en_preparation: 0.0,
      bons_en_preparation: [],
      depart: { unite: 'Palette', contenance: 256.0, quantite: 5632.0, unites: 22.0 },
    },
  ],
}

export function planEssai(autres: Partial<PlanAchat> = {}): PlanAchat {
  return structuredClone({ ...PLAN, ...autres })
}

export function groupeEssai(autres: Partial<GroupeFournisseur> = {}): GroupeFournisseur {
  const premier = PLAN.fournisseurs[0]
  if (!premier) throw new Error('Plan d’essai sans fournisseur.')
  return { ...premier, ...autres }
}

export function lignePlanEssai(autres: Partial<LignePlan> = {}): LignePlan {
  const premiere = PLAN.lignes[0]
  if (!premiere) throw new Error('Plan d’essai sans ligne.')
  return { ...structuredClone(premiere), ...autres }
}

export function preparationEssai(autres: Partial<Preparation> = {}): Preparation {
  return structuredClone({ ...PREPARATION, ...autres })
}

export function lignePreparationEssai(autres: Partial<LignePreparation> = {}): LignePreparation {
  const premiere = PREPARATION.lignes[0]
  if (!premiere) throw new Error('Préparation d’essai sans ligne.')
  return { ...structuredClone(premiere), ...autres }
}
