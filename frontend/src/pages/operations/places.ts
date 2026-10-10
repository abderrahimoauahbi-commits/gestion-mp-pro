/**
 * Où sont les lots d'une matière (`GET lots?matiere=&date=`, un solde par magasin) et lesquels
 * proposer selon le type et le motif (ECRANS-PRO partie 6, encart de ligne) : une libération ne
 * prend qu'un lot en quarantaine, tout autre transfert qu'un lot hors quarantaine (an. 2) ; un
 * retour au fournisseur montre le fournisseur du lot et, après une première ligne, ne propose
 * plus que les lots du même fournisseur (an. 4).
 */
import { date as dateLisible, kgEtMetres } from '../../lib/format'
import { LIBERATION, type LotSolde, type MagasinFiche, type MotifLu, type TypeOperation } from './types'

export interface Place {
  /** `lot-magasin`. */
  cle: string
  lot_id: number
  lot: string
  matiere_id: number
  reference: string
  designation: string
  magasin_id: number
  magasin: string
  quantite: number
  quarantaine: boolean
  fournisseur: string
  entre_le: string
  poids_bobine: number
  bobines_palette: number
  kg_par_ml: number
}

/** Chaque solde > 0 d'un lot dans un magasin. */
export function placesDeLots(lots: readonly LotSolde[]): Place[] {
  return lots.flatMap((l) =>
    l.magasins
      .filter((g) => g.quantite > 0)
      .map((g) => ({
        cle: `${l.lot_id}-${g.magasin_id}`,
        lot_id: l.lot_id,
        lot: l.lot,
        matiere_id: l.matiere_id,
        reference: l.reference,
        designation: l.designation,
        magasin_id: g.magasin_id,
        magasin: g.magasin,
        quantite: g.quantite,
        quarantaine: g.type === 'quarantaine',
        fournisseur: l.fournisseur,
        entre_le: l.entre_le,
        poids_bobine: l.poids_bobine,
        bobines_palette: l.bobines_palette,
        kg_par_ml: l.kg_par_ml,
      })),
  )
}

/** Les places proposées pour ce type, ce motif et ce fournisseur imposé. */
export function placesProposees(
  places: readonly Place[],
  type: TypeOperation,
  motif: MotifLu | undefined,
  fournisseur: string | null,
): Place[] {
  if (type === 'transfert') {
    const liberation = motif?.libelle === LIBERATION
    return places.filter((p) => p.quarantaine === liberation)
  }
  if (type === 'retour_fournisseur' && fournisseur) return places.filter((p) => p.fournisseur === fournisseur)
  return [...places]
}

/** « [MATIÈRE · ]Lot L-12 · MAG[ (quarantaine)] · 120,0 kg · entré le … »[ · fournisseur].
 * `avecMatiere` (choix par dépôt, toutes matières) montre la matière et la rend cherchable. */
export function optionDePlace(p: Place, type: TypeOperation, avecMatiere = false) {
  return {
    id: p.cle,
    titre: `${avecMatiere ? `${p.reference} · ` : ''}Lot ${p.lot} · ${p.magasin}${p.quarantaine ? ' (quarantaine)' : ''}`,
    sous: [
      kgEtMetres(p.quantite, p.kg_par_ml),
      p.entre_le ? `entré le ${dateLisible(p.entre_le)}` : '',
      type === 'retour_fournisseur' ? p.fournisseur : '',
    ]
      .filter(Boolean)
      .join(' · '),
    recherche: avecMatiere ? `${p.reference} ${p.designation}` : undefined,
  }
}

/** Ce que l'aide dit quand aucun lot n'est proposé. */
export function aucunLot(type: TypeOperation, motif: MotifLu | undefined, places: readonly Place[]): string {
  if (type === 'transfert' && motif?.libelle === LIBERATION)
    return 'Aucun lot de cette matière n’est en quarantaine'
  if (type === 'transfert' && places.length && places.every((p) => p.quarantaine))
    return `Tous les lots de cette matière sont en quarantaine : ils ne sortent qu’avec « ${LIBERATION} »`
  return 'Aucun lot en stock pour cette matière'
}

/** Les magasins d'arrivée d'un transfert : hors départ ; mise en quarantaine → quarantaine seulement. */
export function destinations(
  magasins: readonly MagasinFiche[],
  depart: number | null,
  motif: MotifLu | undefined,
): MagasinFiche[] {
  const actifs = magasins.filter((g) => g.actif && g.id !== depart)
  if (motif?.libelle === 'Mise en quarantaine') return actifs.filter((g) => g.type === 'quarantaine')
  if (motif?.libelle === LIBERATION) return actifs.filter((g) => g.type !== 'quarantaine')
  return actifs
}
