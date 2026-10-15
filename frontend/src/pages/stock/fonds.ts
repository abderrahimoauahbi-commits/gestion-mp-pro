/**
 * Les fonds de lot (lot FOND-DE-LOT, décision de Mohamed du 15/10/2026) : ce qui reste d'un lot
 * dans un magasin, > 0 et sous le seuil de rebut (réglage « Seuil de rebut », 100 g par défaut,
 * lu dans le contexte de session). Le serveur pose la marque (`fond_de_lot` sur le lot et sur
 * chaque solde) ; l'écran l'écrit « fond de lot (< 100 g) », la compte, et offre « Mettre au
 * rebut » (route 258) à qui y a droit.
 */
import type { Role } from '../../lib/types'
import { nombre } from '../../lib/format'
import { estQuarantaine, type LotSolde, type SoldeMagasin } from './types'

/** « 100 g » sous le kilo, « 2 kg » au-dessus — la même écriture que le serveur. */
export function poidsFond(kg: number): string {
  if (kg < 1) return `${nombre(Math.round(kg * 1000))} g`
  return `${nombre(kg, 0, 2)} kg`
}

/** La marque des écrans : « fond de lot (< 100 g) » ; '' quand le seuil est désactivé (0). */
export function marqueFond(seuil: number | null | undefined): string {
  if (!seuil || seuil <= 0) return ''
  return `fond de lot (< ${poidsFond(seuil)})`
}

/** Les soldes d'un lot qui sont des fonds de lot. */
export function soldesFonds(l: Pick<LotSolde, 'magasins'>): SoldeMagasin[] {
  return l.magasins.filter((g) => g.fond_de_lot && g.quantite > 0)
}

/** Combien de fonds de lot (un par lot et magasin) et ce qu'ils pèsent, dans une liste. */
export function fondsDe(lots: readonly LotSolde[]): { nombre: number; kg: number } {
  let n = 0
  let kg = 0
  for (const l of lots)
    for (const g of soldesFonds(l)) {
      n += 1
      kg += g.quantite
    }
  return { nombre: n, kg: Math.round(kg * 1000) / 1000 }
}

/**
 * Qui met ce solde au rebut sans motif : un fond de lot pour la direction et les achats ; pour
 * l'alimentation, un fond de lot hors quarantaine (la quarantaine est une décision des achats
 * ou de la direction). Au-dessus du seuil : la direction seule, avec un motif (`motifExige`).
 */
export function rebutPermis(
  role: Role,
  g: SoldeMagasin,
): { permis: boolean; motifExige: boolean; raison: string } {
  if (g.quantite <= 0) return { permis: false, motifExige: false, raison: 'Rien dans ce magasin.' }
  if (g.fond_de_lot) {
    if (role === 'alimentation' && estQuarantaine(g.type))
      return {
        permis: false,
        motifExige: false,
        raison:
          'Un lot en quarantaine ne se met pas au rebut depuis l’atelier : décision de la direction ou des achats.',
      }
    return { permis: role !== 'administrateur', motifExige: false, raison: '' }
  }
  if (role === 'direction') return { permis: true, motifExige: true, raison: '' }
  return {
    permis: false,
    motifExige: false,
    raison:
      'Ce n’est pas un fond de lot : seule la direction met au rebut au-dessus du seuil, avec un motif.',
  }
}

/** La question courte d'une ligne de liste : « Rebut : 56 g du lot HT-… dans « Morocco » ? ». */
export function questionCourte(l: Pick<LotSolde, 'lot'>, g: SoldeMagasin): string {
  return `Rebut : ${poidsFond(g.quantite)} du lot ${l.lot} dans « ${g.magasin} » ?`
}

/** La question de la confirmation : « Mettre au rebut 56 g du lot HT-… dans Morocco ? ». */
export function questionRebut(l: Pick<LotSolde, 'lot' | 'reference'>, g: SoldeMagasin): string {
  return `Mettre au rebut ${poidsFond(g.quantite)} du lot ${l.lot} (${l.reference}) dans « ${g.magasin} » ? Le stock baisse d’autant, par un ajustement « Rebut » validé tout de suite.`
}
