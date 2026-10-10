/**
 * L'encart « Nouvelle ligne » / « Modifier la ligne RÉF », sans écran : son état, ce qui manque
 * pour ajouter la ligne (an. 5), et la ligne qu'il produit. Le sens d'un ajustement est « + » pour
 * une matière retrouvée ou un lot qui n'est pas en stock, et « − » y est impossible (an. 3).
 */
import type { Unite } from '../../lib/unites'
import { nombre } from '../../lib/format'
import type { Place } from './places'
import type { LigneSaisie } from './saisie'
import { MATIERE_RETROUVEE, type MatiereResume, type MotifLu, type TypeOperation } from './types'

/** La place choisie pour un lot qui n'est pas en stock (ajustement « matière retrouvée »). */
export const NOUVEAU_LOT = 'nouveau'

/** Un type qui part d'un lot déjà en stock : on peut alors chercher par dépôt de départ (an. 2). */
export const partDunLot = (type: TypeOperation) =>
  type === 'transfert' || type === 'ajustement' || type === 'retour_fournisseur'

export interface EtatEncart {
  matiere: number | null
  /** Le dépôt de départ, critère de recherche facultatif : voir les lots d'un magasin, toutes
   * matières, pour choisir ce qui bouge (an. 2, « partir du dépôt »). `null` : tous les dépôts. */
  depart: number | null
  /** `lot-magasin`, `nouveau`, ou un identifiant de lot (retour des machines). */
  place: string | null
  lot_numero: string
  lot_interne: boolean
  magasin: number | null
  vers: number | null
  sens: '+' | '-'
  kg: number | null
  unite: Unite
  prix: number | null
  devise: string
}

export const ENCART_VIERGE: EtatEncart = {
  matiere: null,
  depart: null,
  place: null,
  lot_numero: '',
  lot_interne: false,
  magasin: null,
  vers: null,
  sens: '-',
  kg: null,
  unite: 'kg',
  prix: null,
  devise: 'MAD',
}

/** L'encart rouvert sur une ligne déjà posée. */
export function encartDe(l: LigneSaisie, type: TypeOperation): EtatEncart {
  const nouveau = l.lot_id == null
  return {
    matiere: l.matiere_id,
    depart: null,
    place:
      type === 'ouverture'
        ? null
        : nouveau
          ? NOUVEAU_LOT
          : type === 'retour_machine'
            ? String(l.lot_id)
            : `${l.lot_id}-${l.magasin_id}`,
    lot_numero: l.lot_numero,
    lot_interne: l.lot_interne,
    magasin: l.magasin_id,
    vers: l.magasin_destination_id,
    sens: l.quantite < 0 ? '-' : '+',
    kg: Math.abs(l.quantite),
    unite: 'kg',
    prix: l.prix,
    devise: l.devise,
  }
}

/** Le lot est-il à créer (ouverture, matière retrouvée) ? */
export const lotACreer = (type: TypeOperation, e: EtatEncart) =>
  type === 'ouverture' || (type === 'ajustement' && e.place === NOUVEAU_LOT)

/** Le sens est-il imposé à « + » (matière retrouvée, lot pas en stock) ? */
export const sensImpose = (type: TypeOperation, e: EtatEncart, motif: MotifLu | undefined) =>
  type === 'ajustement' && (e.place === NOUVEAU_LOT || motif?.libelle === MATIERE_RETROUVEE)

/** Ce qui manque pour ajouter la ligne. */
export function manqueEncart(
  type: TypeOperation,
  e: EtatEncart,
  place: Place | undefined,
  sortiNet?: number,
): string[] {
  const manque: string[] = []
  if (e.matiere == null) return ['la matière']
  if (lotACreer(type, e)) {
    if (!e.lot_interne && !e.lot_numero.trim()) manque.push('le numéro de lot (ou cocher « Lot interne »)')
    if (e.magasin == null) manque.push('le magasin')
  } else if (e.place == null) manque.push('le lot')
  if (type === 'retour_machine' && e.magasin == null) manque.push('le magasin')
  if (type === 'transfert' && e.vers == null) manque.push('le magasin de destination')
  if (e.kg == null || e.kg <= 0) manque.push('la quantité')
  const sort =
    type === 'transfert' || type === 'retour_fournisseur' || (type === 'ajustement' && e.sens === '-')
  if (sort && place && e.kg != null && e.kg > place.quantite + 0.001)
    manque.push(`une quantité qui ne dépasse pas les ${nombre(place.quantite, 0, 2)} kg du lot`)
  if (type === 'retour_machine' && sortiNet != null && e.kg != null && e.kg > sortiNet + 0.001)
    manque.push(`une quantité qui ne dépasse pas les ${nombre(sortiNet, 0, 2)} kg partis pour l’ordre`)
  if (type === 'ouverture' && e.prix == null) manque.push('le prix au kilo')
  return manque
}

/** La ligne que produit l'encart. */
export function ligneDeLEncart(
  type: TypeOperation,
  e: EtatEncart,
  m: MatiereResume,
  place: Place | undefined,
  noms: { magasin: (id: number | null) => string; lot: (id: number) => string },
  cle: string,
): LigneSaisie {
  const nouveau = lotACreer(type, e)
  const magasinId = place && !nouveau ? place.magasin_id : (e.magasin ?? 0)
  const lotId = nouveau ? null : place ? place.lot_id : Number(e.place)
  return {
    cle,
    matiere_id: m.id,
    reference: m.reference,
    kg_par_ml: m.kg_par_ml,
    lot_id: lotId,
    lot: nouveau
      ? e.lot_interne
        ? 'LOT INTERNE'
        : e.lot_numero.trim()
      : place
        ? place.lot
        : noms.lot(lotId ?? 0),
    lot_numero: nouveau && !e.lot_interne ? e.lot_numero.trim() : '',
    lot_interne: nouveau && e.lot_interne,
    magasin_id: type === 'retour_machine' ? (e.magasin ?? 0) : magasinId,
    magasin: noms.magasin(type === 'retour_machine' ? e.magasin : magasinId),
    magasin_destination_id: type === 'transfert' ? e.vers : null,
    magasin_destination: type === 'transfert' ? noms.magasin(e.vers) : '',
    quantite: type === 'ajustement' && e.sens === '-' ? -(e.kg ?? 0) : (e.kg ?? 0),
    prix: type === 'ouverture' ? (e.prix ?? 0) : 0,
    devise: type === 'ouverture' ? e.devise : 'MAD',
    quarantaine: place?.quarantaine ?? false,
    disponible: place && !nouveau ? place.quantite : null,
    fournisseur: place?.fournisseur ?? m.fournisseur ?? '',
  }
}

/** L'encart a-t-il été rempli (fermer demande alors confirmation, an. 25) ? */
export const encartRempli = (e: EtatEncart) => e.matiere != null
