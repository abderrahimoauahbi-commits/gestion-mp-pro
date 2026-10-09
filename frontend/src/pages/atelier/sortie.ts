/**
 * Les règles d'une sortie vers les machines (ECRANS-PRO partie 3, « Logique de l'envoi ») :
 * prises de lots en kg, bobines ou palettes, fils regroupés par matière, écarts au prévu de la
 * recette, dépassements, contenances manquantes, corps envoyé au serveur. Fonctions pures, le
 * hook `useSaisieSortie` les assemble.
 */
import { arrondi } from '../../lib/format'
import { contenance, depuisKg, direArrondi, versKg, type Conditionnement, type Unite } from '../../lib/unites'
import type { LigneOrdre, LigneProposee, LotSolde } from './types'

/** Un lot pris pour un fil, dans l'unité où on le compte. */
export interface Prise {
  cle: string
  matiere_id: number
  reference: string
  designation: string
  kg_par_ml: number
  poids_bobine: number
  bobines_palette: number
  lot_id: number
  lot: string
  unite: Unite
  quantite: number
  /** « arrondi : 7,49 kg au lieu de 7,5 kg » après un changement d'unité. */
  arrondi?: string
}

/** Une qualité à fabriquer (une fois par ordre) et ses m². */
export interface Fabrication {
  qualite: number | null
  m2: number
}

/** Un fil de l'ordre : ce que les recettes en demandent, ce qu'on en prend. */
export interface Fil {
  matiere_id: number
  reference: string
  kg_par_ml: number
  besoin?: LigneProposee
  prises: Prise[]
  sorti: number
  ecart: number | null
}

export const conditionnement = (p: Prise): Conditionnement => ({
  poidsBobine: p.poids_bobine,
  bobinesPalette: p.bobines_palette,
  kgParMl: p.kg_par_ml,
})

/** Les kilos d'une prise (0 si l'unité n'a pas de contenance connue). */
export function kgDe(p: Prise): number {
  return versKg(p.quantite, p.unite, conditionnement(p)) ?? 0
}

let compteur = 0
const nouvelleCle = () => `p${Date.now().toString(36)}${++compteur}`

interface MatiereDuLot {
  matiere_id: number
  reference: string
  designation: string
  kg_par_ml: number
  poids_bobine: number
  bobines_palette: number
}

/** Une prise d'un lot, en kilos. */
export function priseDe(
  m: MatiereDuLot,
  lot: { lot_id: number; lot: string; poids_bobine?: number },
  quantite = 0,
): Prise {
  return {
    cle: nouvelleCle(),
    matiere_id: m.matiere_id,
    reference: m.reference,
    designation: m.designation,
    kg_par_ml: m.kg_par_ml,
    poids_bobine: lot.poids_bobine || m.poids_bobine,
    bobines_palette: m.bobines_palette,
    lot_id: lot.lot_id,
    lot: lot.lot,
    unite: 'kg',
    quantite: arrondi(quantite, 3),
  }
}

/** La ligne d'un brouillon rouvert : en bobines si le compte tombe juste (P2), sinon au gramme. */
export function priseRouverte(l: LigneOrdre): Prise {
  const p = priseDe(l, { lot_id: l.lot_id, lot: l.lot, poids_bobine: l.poids_bobine }, l.quantite)
  return l.bobines != null && l.bobines >= 1 ? { ...p, unite: 'bobine', quantite: l.bobines } : p
}

/** La prise d'un lot choisi dans la liste des lots du magasin (fil ajouté à la main). */
export function priseDuSolde(x: LotSolde): Prise {
  return priseDe(x, { lot_id: x.lot_id, lot: x.lot, poids_bobine: x.poids_bobine })
}

/** Changer d'unité garde la quantité, arrondie comme on la compte, et le dit. */
export function changerUnite(p: Prise, unite: Unite): Prise {
  if (unite === p.unite) return p
  const avant = kgDe(p)
  const conversion = depuisKg(avant, unite, conditionnement(p))
  if (!conversion) return { ...p, unite, quantite: 0, arrondi: undefined }
  return { ...p, unite, quantite: conversion.quantite, arrondi: direArrondi(conversion, avant) || undefined }
}

/** Les fils de l'ordre : ceux des recettes d'abord, puis ceux ajoutés à la main. */
export function regrouper(besoins: readonly LigneProposee[], prises: readonly Prise[]): Fil[] {
  const fils = new Map<number, Fil>()
  for (const b of besoins)
    fils.set(b.matiere_id, {
      matiere_id: b.matiere_id,
      reference: b.reference,
      kg_par_ml: b.kg_par_ml,
      besoin: b,
      prises: [],
      sorti: 0,
      ecart: null,
    })
  for (const p of prises) {
    const f = fils.get(p.matiere_id) ?? {
      matiere_id: p.matiere_id,
      reference: p.reference,
      kg_par_ml: p.kg_par_ml,
      prises: [],
      sorti: 0,
      ecart: null,
    }
    f.prises.push(p)
    fils.set(p.matiere_id, f)
  }
  for (const f of fils.values()) {
    f.sorti = arrondi(
      f.prises.reduce((t, p) => t + kgDe(p), 0),
      3,
    )
    f.ecart = f.besoin ? arrondi(f.sorti - f.besoin.prevu, 3) : null
  }
  return [...fils.values()]
}

/** Écart d'un fil au prévu : « conforme » sous 0,05 kg ou 0,5 % ; sinon signé, avec un ton. */
export function ecartLisible(
  ecart: number | null,
  prevu: number,
): { conforme: boolean; ton: 'ok' | 'neutre' | 'attention' | 'critique'; relatif: number } | null {
  if (ecart == null || !prevu) return null
  const relatif = ecart / prevu
  if (Math.abs(ecart) < 0.05 || Math.abs(relatif) < 0.005) return { conforme: true, ton: 'ok', relatif }
  const ton = Math.abs(relatif) <= 0.05 ? 'neutre' : ecart > 0 ? 'attention' : 'critique'
  return { conforme: false, ton, relatif }
}

/** Un fil « tout est conforme » : écart conforme, sans manque, sans dépassement ni contenance manquante. */
export function filConforme(f: Fil, dispo: (p: Prise) => number): boolean {
  if (!f.besoin || f.besoin.manque > 0.05) return false
  if (!ecartLisible(f.ecart, f.besoin.prevu)?.conforme) return false
  return f.prises.every((p) => !depasse(p, dispo(p)) && contenance(conditionnement(p), p.unite) != null)
}

/** Vrai si la prise demande plus que ce que porte le lot (`dispo` < 0 : pas encore connu). */
export function depasse(p: Prise, dispo: number): boolean {
  return dispo >= 0 && kgDe(p) > dispo + 0.001
}

/** Les lignes envoyées au serveur (`LigneSaisie`), quantités > 0 seulement. */
export function lignesDuCorps(prises: readonly Prise[]) {
  return prises
    .filter((p) => p.quantite > 0)
    .map((p) => ({ lot_id: p.lot_id, matiere_id: p.matiere_id, quantite: p.quantite, unite: p.unite }))
}

/** Les qualités envoyées au serveur. */
export function qualitesDuCorps(horsRecette: boolean, fabrications: readonly Fabrication[]) {
  if (horsRecette) return []
  return fabrications.flatMap((f) => (f.qualite == null ? [] : [{ qualite_id: f.qualite, m2: f.m2 }]))
}

/** Ce qui manque pour calculer la proposition, dans l'ordre où on remplit (raison sous le bouton). */
export function manqueDemande(e: {
  magasin: number | null
  jour: string
  horsRecette: boolean
  fabrications: readonly Fabrication[]
}): string {
  if (e.magasin == null) return 'Choisir le magasin d’où sort la matière'
  if (!e.jour) return 'Choisir la date'
  if (e.horsRecette) return ''
  if (!e.fabrications.length) return 'Ajouter une qualité à fabriquer'
  if (e.fabrications.some((f) => f.qualite == null)) return 'Choisir la qualité à fabriquer'
  if (e.fabrications.some((f) => !(f.m2 > 0))) return 'Saisir les mètres carrés à fabriquer'
  return ''
}
