/**
 * Les libellés du moteur (« 🔥 TIER 1 », « 🚨 BC URGENT », « 🔴 RUPTURE ») rendus sans émoticône
 * (REGLES-ECRAN § 5) : l'écran en fait des badges de la table unique (`lib/statuts.ts`). Les unités
 * de commande se disent avec leur contenance (« Palette (862,4 kg) »), jamais « ml ».
 */
import { INSECABLE, nombre } from '../../lib/format'
import type { Ton } from '../../lib/statuts'
import type { BonEnPreparation, GroupeFournisseur } from './types'

/** La clé de priorité d'un libellé du moteur (« 🔥 TIER 1 » → « TIER_1 »), `null` sinon. */
export function cleTier(texte: string | null | undefined): string | null {
  const m = /TIER\s*(\d)/i.exec(texte ?? '')
  return m ? `TIER_${m[1]}` : null
}

/** « Tier 1 » … « Tier 4 », sans émoticône. */
export function libelleTier(texte: string | null | undefined): string {
  const m = /TIER\s*(\d)/i.exec(texte ?? '')
  return m ? `Tier ${m[1]}` : '—'
}

export type CleUrgence = 'urgent' | 'a_grouper' | 'standard'

/** L'urgence d'un fournisseur (« 🚨 BC URGENT », « 📋 BC groupé », « 📝 Standard ») ; `null` : rien à commander. */
export function cleUrgence(texte: string | null | undefined): CleUrgence | null {
  const t = (texte ?? '').toUpperCase()
  if (t.includes('URGENT')) return 'urgent'
  if (t.includes('GROUP')) return 'a_grouper'
  if (t.includes('STANDARD')) return 'standard'
  return null
}

/** Le texte du badge : « Urgent · 2 rupt. · 1 crit. · 3 urg. », « À grouper », « Standard ». */
export function texteUrgence(g: GroupeFournisseur): string {
  const cle = cleUrgence(g.urgence)
  if (cle !== 'urgent') return cle === 'a_grouper' ? 'À grouper' : cle === 'standard' ? 'Standard' : '—'
  const details = [
    g.ruptures ? `${nombre(g.ruptures)} rupt.` : '',
    g.critiques ? `${nombre(g.critiques)} crit.` : '',
    g.urgents ? `${nombre(g.urgents)} urg.` : '',
  ].filter(Boolean)
  return ['Urgent', ...details].join(' · ')
}

export const TON_URGENCE: Record<CleUrgence, Ton> = {
  urgent: 'rupture',
  a_grouper: 'attention',
  standard: 'neutre',
}

/** « kg », « Palette (862,4 kg) », « Fût (200 kg) ». */
export function libelleUnite(unite: string, contenance: number): string {
  if (unite === 'kg' || !contenance || contenance === 1) return unite
  return `${unite} (${nombre(contenance, 0, 3)}${INSECABLE}kg)`
}

/** « 7 palettes », « 1 Fût », « 12,5 kg » : une quantité dans son unité de commande. */
export function quantiteEnUnite(n: number, unite: string): string {
  if (unite === 'kg') return `${nombre(n, 0, 1)}${INSECABLE}kg`
  const pluriel = n >= 2 && !/s$/i.test(unite) ? `${unite.toLowerCase()}s` : unite.toLowerCase()
  return `${nombre(n, 0, 2)}${INSECABLE}${pluriel}`
}

/** « Brouillon, BC-2026-0012 » : les bons pas encore partis qui portent déjà la matière. */
export function bonsEnPreparation(bons: readonly BonEnPreparation[]): string {
  return bons.map((b) => b.numero || 'Brouillon').join(', ')
}
