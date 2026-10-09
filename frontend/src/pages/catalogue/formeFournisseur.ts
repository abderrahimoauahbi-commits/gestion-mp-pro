/**
 * La saisie d'une fiche fournisseur, sans écran : la forme, le corps envoyé (la fiche entière,
 * API-PRO § 1.24) et ce qui manque pour enregistrer (dit avant le clic, R6), aux bornes du
 * serveur (`api/fournisseurs/schemas.py`).
 */
import { messageNombre } from '../../composants/saisie/Nombre'
import { DELAI_MAX } from './bornes'
import type { Fournisseur, FournisseurCorps } from './types'

export interface FormeFournisseur {
  nom: string
  code: string
  pays: string
  contact: string
  telephone: string
  email: string
  devise: string
  delai_jours: number | null
  couverture_commande_jours: number | null
  mode_paiement: string
  delai_paiement_jours: number | null
  conditions_paiement: string
  incoterm: string
  port_chargement: string
  banque: string
  notes: string
  actif: boolean
}

export const INCOTERMS = [
  'EXW',
  'FCA',
  'FAS',
  'FOB',
  'CFR',
  'CIF',
  'CPT',
  'CIP',
  'DAP',
  'DPU',
  'DDP',
] as const
export const MODES_PAIEMENT = [
  'Virement',
  'Crédit documentaire (LC)',
  'Remise documentaire',
  'Traite / LCN',
  'Chèque',
  'Espèces',
  'Open account',
] as const

export function versFormeFournisseur(f: Fournisseur | null): FormeFournisseur {
  return {
    nom: f?.nom ?? '',
    code: f?.code ?? '',
    pays: f?.pays ?? '',
    contact: f?.contact ?? '',
    telephone: f?.telephone ?? '',
    email: f?.email ?? '',
    devise: f?.devise ?? 'MAD',
    delai_jours: f ? f.delai_jours : 60,
    couverture_commande_jours: f?.couverture_commande_jours || null,
    mode_paiement: f?.mode_paiement ?? '',
    delai_paiement_jours: f?.delai_paiement_jours || null,
    conditions_paiement: f?.conditions_paiement ?? '',
    incoterm: f?.incoterm ?? '',
    port_chargement: f?.port_chargement ?? '',
    banque: f?.banque ?? '',
    notes: f?.notes ?? '',
    actif: f?.actif ?? true,
  }
}

export function corpsFournisseur(f: FormeFournisseur): Omit<FournisseurCorps, 'version'> {
  const t = (s: string) => s.trim()
  return {
    nom: t(f.nom),
    code: t(f.code),
    pays: t(f.pays),
    contact: t(f.contact),
    telephone: t(f.telephone),
    email: t(f.email),
    devise: f.devise,
    delai_jours: f.delai_jours ?? 0,
    couverture_commande_jours: f.couverture_commande_jours ?? 0,
    mode_paiement: t(f.mode_paiement),
    delai_paiement_jours: f.delai_paiement_jours ?? 0,
    conditions_paiement: t(f.conditions_paiement),
    incoterm: t(f.incoterm),
    port_chargement: t(f.port_chargement),
    banque: t(f.banque),
    notes: t(f.notes),
    actif: f.actif,
  }
}

export const memeFournisseur = (a: FormeFournisseur, b: FormeFournisseur) =>
  JSON.stringify(a) === JSON.stringify(b)

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Ce qui manque pour enregistrer (les mots de Gestion MP). */
export function manquesFournisseur(f: FormeFournisseur): string[] {
  const m: string[] = []
  if (f.nom.trim().length < 2) m.push('le nom')
  if (!f.delai_jours) m.push('le délai d’approvisionnement')
  const bornes = { min: 0, max: DELAI_MAX, decimales: 0 }
  if (messageNombre(f.delai_jours, bornes)) m.push('un délai de deux ans au plus')
  if (messageNombre(f.couverture_commande_jours, bornes)) m.push('une couverture de deux ans au plus')
  if (messageNombre(f.delai_paiement_jours, bornes)) m.push('un délai de paiement de deux ans au plus')
  if (f.email.trim() && !EMAIL.test(f.email.trim())) m.push('un e-mail de la forme nom@domaine.ma')
  return m
}

/** Le classement du score en code de `lib/statuts.ts` (« À surveiller » → `a_surveiller`). */
export function codeClassement(texte: string): string {
  return texte
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z ]/g, '')
    .trim()
    .replace(/\s+/g, '_')
}

/** Le délai mesuré dépasse-t-il de plus de 20 % le déclaré, sur 3 livraisons au moins (P7-24) ? */
export function delaiDepasse(f: Fournisseur): boolean {
  return (
    f.delai_mesure_jours != null && f.livraisons_mesurees >= 3 && f.delai_mesure_jours > 1.2 * f.delai_jours
  )
}
