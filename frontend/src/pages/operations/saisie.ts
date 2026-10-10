/**
 * La saisie d'une opération, sans écran (ECRANS-PRO partie 6, « Fenêtre d'une opération ») : le
 * brouillon local, ce qui manque pour l'enregistrer, les lignes que le motif rend incompatibles
 * (quarantaine, an. 2), la suspension par un inventaire ouvert (an. 20, par périmètre), le corps de
 * `POST/PUT operations`, la question de « Valider ».
 */
import { messageDate } from '../../composants/saisie/DateChamp'
import { nombre } from '../../lib/format'
import type { InventaireOuvert } from '../../lib/types-coque'
import {
  LIBERATION,
  MISE_EN_QUARANTAINE,
  type MagasinFiche,
  type MotifLu,
  type OperationFiche,
  type TypeOperation,
} from './types'

export interface LigneSaisie {
  /** Identifiant local (la ligne d'une opération lue, ou un compteur). */
  cle: string
  matiere_id: number
  reference: string
  kg_par_ml: number
  lot_id: number | null
  /** Le numéro affiché : celui du lot choisi, ou celui à créer. */
  lot: string
  lot_numero: string
  lot_interne: boolean
  magasin_id: number
  magasin: string
  magasin_destination_id: number | null
  magasin_destination: string
  /** En kilos ; signée pour un ajustement. */
  quantite: number
  prix: number
  devise: string
  /** Le lot était en quarantaine dans son magasin de départ (pour revérifier au changement de motif). */
  quarantaine: boolean
  /** Ce que le lot portait dans ce magasin quand on l'a choisi (dépassement). */
  disponible: number | null
  fournisseur: string
}

export interface SaisieOperation {
  type: TypeOperation
  date: string
  motif_id: number | null
  commentaire: string
  ordre_id: number | null
  lignes: readonly LigneSaisie[]
}

/** Le brouillon local d'une opération lue. */
export function saisieDe(o: OperationFiche, magasins: readonly MagasinFiche[]): SaisieOperation {
  const quarantaine = new Set(magasins.filter((g) => g.type === 'quarantaine').map((g) => g.id))
  return {
    type: o.type,
    date: o.date,
    motif_id: o.motif_id,
    commentaire: o.commentaire,
    ordre_id: o.ordre_id,
    lignes: o.lignes.map((l) => ({
      cle: `l${l.id}`,
      matiere_id: l.matiere_id,
      reference: l.reference,
      kg_par_ml: l.kg_par_ml,
      lot_id: l.lot_id,
      lot: l.lot,
      lot_numero: l.lot_id == null && !l.lot_interne ? l.lot : '',
      lot_interne: l.lot_interne,
      magasin_id: l.magasin_id,
      magasin: l.magasin,
      magasin_destination_id: l.magasin_destination_id,
      magasin_destination: l.magasin_destination,
      quantite: l.quantite,
      prix: l.prix ?? 0,
      devise: l.devise ?? 'MAD',
      quarantaine: quarantaine.has(l.magasin_id),
      disponible: null,
      fournisseur: o.fournisseur,
    })),
  }
}

/** Le corps de `POST operations` (création) ou `PUT operations/{id}` (avec la version). */
export function corpsOperation(s: SaisieOperation) {
  return {
    type: s.type,
    date: s.date,
    ordre_id: s.ordre_id,
    motif_id: s.motif_id,
    commentaire: s.commentaire.trim(),
    lignes: s.lignes.map((l) => ({
      matiere_id: l.matiere_id,
      lot_id: l.lot_id,
      lot_numero: l.lot_id == null && !l.lot_interne ? l.lot_numero.trim() : '',
      lot_interne: l.lot_id == null && l.lot_interne,
      magasin_id: l.magasin_id,
      magasin_destination_id: s.type === 'transfert' ? l.magasin_destination_id : null,
      quantite: l.quantite,
      unite: 'kg',
      prix: s.type === 'ouverture' ? l.prix : 0,
      devise: s.type === 'ouverture' ? l.devise : 'MAD',
    })),
  }
}

/** Les observations exigées, et leur longueur minimale (ajustement 5, mise en quarantaine 3). */
export function observationsExigees(type: TypeOperation, motif: MotifLu | undefined): number {
  if (type === 'ajustement') return 5
  return motif?.libelle === MISE_EN_QUARANTAINE ? 3 : 0
}

/** Le motif est-il obligatoire pour ce type ? */
export const motifExige = (type: TypeOperation) =>
  type === 'ajustement' || type === 'retour_fournisseur' || type === 'retour_machine'

/** Ce qui manque pour enregistrer (raison du bouton, qui suit l'état). */
export function manqueOperation(s: SaisieOperation, motif: MotifLu | undefined, min?: string, max?: string) {
  const manque: string[] = []
  if (!s.lignes.length) manque.push('au moins une ligne')
  if (motifExige(s.type) && s.motif_id == null) manque.push('le motif')
  const n = observationsExigees(s.type, motif)
  if (n && s.commentaire.trim().length < n)
    manque.push(
      s.type === 'ajustement'
        ? 'les observations (ce qui a été constaté)'
        : 'les observations (ce qui est douteux)',
    )
  if (!s.date || messageDate(s.date, min, max))
    manque.push('une date qui ne soit pas dans le futur ni en période close')
  return manque
}

/** Une ligne de transfert que le motif rend impossible (quarantaine, an. 2) : sa raison, ou ''. */
export function incompatibilite(l: LigneSaisie, type: TypeOperation, motif: MotifLu | undefined): string {
  if (type !== 'transfert') return ''
  const quoi = `« ${l.reference} », lot ${l.lot}`
  if (motif?.libelle === LIBERATION && !l.quarantaine)
    return `${quoi} : une libération de quarantaine part d’un magasin de quarantaine`
  if (motif?.libelle !== LIBERATION && l.quarantaine)
    return `${quoi} : un lot en quarantaine ne sort qu’avec le motif « ${LIBERATION} »`
  return ''
}

/** Les suspensions par un inventaire ouvert, dès le choix des lots (an. 20, par périmètre). */
export function suspensions(
  lignes: readonly LigneSaisie[],
  ouverts: readonly InventaireOuvert[],
  magasins: readonly MagasinFiche[],
): string[] {
  const code = (id: number | null) => magasins.find((g) => g.id === id)?.code
  const raisons = lignes.flatMap((l) =>
    [l.magasin_id, l.magasin_destination_id].flatMap((id) =>
      ouverts
        .filter(
          (o) =>
            o.matieres.includes(l.matiere_id) && id != null && (o.magasin == null || o.magasin === code(id)),
        )
        .map(
          (o) => `l’inventaire ${o.numero} compte « ${l.reference} » (${o.magasin ?? 'tous les magasins'})`,
        ),
    ),
  )
  return [...new Set(raisons)]
}

/** Ce qu'une ligne retire du lot dans son magasin de départ (kg). */
export function retrait(type: TypeOperation, l: Pick<LigneSaisie, 'quantite'>): number {
  if (type === 'ouverture' || type === 'retour_machine') return 0
  return type === 'ajustement' ? Math.max(0, -l.quantite) : l.quantite
}

/** Les lignes dont la quantité dépasse ce que porte le lot (an. 6 : un blocage, pas un avertissement). */
export function depassements(s: SaisieOperation): string[] {
  return s.lignes
    .filter((l) => l.disponible != null && retrait(s.type, l) > l.disponible + 0.001)
    .map((l) => `« ${l.reference} », lot ${l.lot} : plus que les ${nombre(l.disponible, 0, 2)} kg du lot`)
}

/** La question de « Valider ». */
export function questionValider(n: number): string {
  return `Valider ? Le stock bouge maintenant (${nombre(n)} ligne(s)) ; ensuite l’opération ne se modifie plus.`
}
