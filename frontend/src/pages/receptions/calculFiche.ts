/**
 * La fiche d'une réception, sans écran (ECRANS-PRO 4.17) : les blocages regroupés (dix-neuf lignes
 * sans pesée font une phrase, pas dix-neuf), l'échéance dite en clair, la question de la
 * validation, et le corps de la correction de facture (champ inchangé : absent).
 */
import { date, nombre } from '../../lib/format'
import { joursDepuis } from '../../lib/heure'
import type { FactureCorrection, ReceptionFiche } from './types'

export function resumerBlocages(liste: readonly string[]): string[] {
  const pesee = liste.filter((b) => b.includes('la pesée est à zéro'))
  const lot = liste.filter((b) => b.includes('le numéro de lot manque'))
  const autres = liste.filter((b) => !pesee.includes(b) && !lot.includes(b))
  return [
    ...autres,
    ...(pesee.length > 2
      ? [`${pesee.length} lignes sans pesée : la saisir, ou marquer la ligne « refusé ».`]
      : pesee),
    ...(lot.length > 2
      ? [`${lot.length} lignes sans numéro de lot (celui de l’étiquette, ou « Lot interne »).`]
      : lot),
  ]
}

/** « échéance 01/04/2027 (dans 12 j) », « … dépassée de 3 j », « échéance aujourd'hui ». */
export function echeanceLisible(iso: string): string {
  const passes = joursDepuis(iso) ?? 0
  if (passes > 0) return `échéance ${date(iso)}, dépassée de ${nombre(passes)} j`
  if (passes === 0) return 'échéance aujourd’hui'
  return `échéance ${date(iso)} (dans ${nombre(-passes)} j)`
}

/** Ce que la validation fera, dit avant le « Oui ». */
export function questionValidation(r: ReceptionFiche): string {
  const entrees = r.lignes.filter((l) => l.qualite !== 'refuse')
  if (!entrees.length)
    return 'Toutes les lignes sont refusées : rien n’entre en stock, la réception reste la trace du refus. Ensuite, elle ne se modifie plus.'
  const quarantaine = entrees.filter((l) => l.qualite === 'reserve').length
  const refusees = r.lignes.length - entrees.length
  const hors = r.lignes.filter((l) => l.hors_tolerance).length
  return (
    `${entrees.length - quarantaine} ligne(s) en stock disponible` +
    (quarantaine ? `, ${quarantaine} en quarantaine` : '') +
    (refusees ? `, ${refusees} refusée(s)` : '') +
    ` — ${nombre(r.pese)} kg.` +
    (hors ? ` ${hors} écart(s) de pesée hors tolérance.` : '') +
    ' Ensuite, elle ne se modifie plus.'
  )
}

export interface FormeFacture {
  numero: string
  date: string
  montant: number | null
  echeance: string
}

export function versFormeFacture(r: ReceptionFiche): FormeFacture {
  const f = r.facture
  return {
    numero: f?.numero ?? '',
    date: f?.date ?? '',
    montant: f?.montant ?? null,
    echeance: f?.echeance ?? '',
  }
}

/** Seuls les champs changés partent ; un numéro vidé détache la facture. */
export function corpsFacture(f: FormeFacture, avant: FormeFacture, version: number): FactureCorrection {
  const c: FactureCorrection = { version }
  if (f.numero.trim() !== avant.numero) c.numero = f.numero.trim() || null
  if (f.date !== avant.date) c.date = f.date || null
  if (f.montant !== avant.montant) c.montant = f.montant || null
  if (f.echeance !== avant.echeance) c.echeance = f.echeance || null
  return c
}

/** Les lots d'une réception, pour les étiquettes. */
export const lotsDe = (r: Pick<ReceptionFiche, 'lots'>) => r.lots.join(',')
