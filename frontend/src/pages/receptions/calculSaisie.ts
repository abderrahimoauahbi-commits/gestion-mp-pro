/**
 * La saisie d'un camion, sans écran (ECRANS-PRO 4.16) : les lignes (d'un bon, ou hors commande),
 * l'écart de pesée et l'excédent comptés **comme le serveur** — tous les lots d'une ligne de bon
 * ensemble (anom. 4.6) —, ce qui serait refusé à la validation, et le corps de `POST /receptions`
 * (un camion en deux devises part en **une** requête : `factures` par devise, anom. 4.5).
 */
import { arrondi } from '../../lib/format'
import type { CommandeFiche, LigneCommande } from '../commandes/types'
import type { Matiere } from '../plan-achat/types'
import type {
  FactureEntree,
  LigneReception,
  LigneReceptionEntree,
  Magasin,
  Qualite,
  ReceptionCreation,
} from './types'

export interface Tolerances {
  pesee: number
  bobine: number
  excedent: number
}

export const TOLERANCES_DEFAUT: Tolerances = { pesee: 0.02, bobine: 0.05, excedent: 0.1 }

export interface LigneSaisie {
  cle: string
  commande_ligne_id: number | null
  commande_id: number | null
  /** Le n° du bon (vide hors commande). */
  commande: string
  matiere_id: number
  reference: string
  designation: string
  kgParMl: number
  poidsBobine: number
  bobinesPalette: number
  /** Commandé et déjà reçu sur la ligne du bon (règle de l'excédent). */
  commandee: number
  dejaRecu: number
  /** Le reste à livrer du moment. */
  attendu: number
  lot_numero: string
  lot_interne: boolean
  quantite_bl: number | null
  quantite_pesee: number | null
  nb_palettes: number | null
  bobines_en_plus: number | null
  magasin_id: number | null
  qualite: Qualite
  observations: string
  /** Le prix au kilo ; `prixConfirme` : celui du bon, non modifiable. */
  prix: number | null
  prixConfirme: boolean
  devise: string
}

let compteur = 0
export const nouvelleCle = () => `l${++compteur}`

const vide = {
  lot_numero: '',
  lot_interne: false,
  quantite_bl: null,
  quantite_pesee: null,
  nb_palettes: null,
  bobines_en_plus: null,
  qualite: 'conforme' as const,
  observations: '',
}

export function ligneDuBon(
  c: CommandeFiche,
  l: LigneCommande,
  m: Matiere | undefined,
  magasin: number | null,
): LigneSaisie {
  return {
    ...vide,
    cle: nouvelleCle(),
    commande_ligne_id: l.id,
    commande_id: c.id,
    commande: c.numero ?? '',
    matiere_id: l.matiere_id,
    reference: l.reference,
    designation: l.designation,
    kgParMl: l.kg_par_ml,
    poidsBobine: m?.poids_bobine ?? 0,
    bobinesPalette: m?.bobines_palette ?? 0,
    commandee: l.quantite,
    dejaRecu: l.recu,
    attendu: l.reste,
    magasin_id: magasin,
    prix: l.prix_confirme ? l.prix : l.prix_catalogue || null,
    prixConfirme: l.prix_confirme && l.prix > 0,
    devise: c.devise,
  }
}

/** Hors commande : le prix se paie dans la devise du fournisseur ; le catalogue n'est proposé que dans cette devise. */
export function ligneHorsCommande(
  m: Matiere,
  deviseFournisseur: string,
  magasin: number | null,
): LigneSaisie {
  const devise = deviseFournisseur || m.devise || 'MAD'
  return {
    ...vide,
    cle: nouvelleCle(),
    commande_ligne_id: null,
    commande_id: null,
    commande: '',
    matiere_id: m.id,
    reference: m.reference,
    designation: m.designation,
    kgParMl: m.kg_par_ml,
    poidsBobine: m.poids_bobine,
    bobinesPalette: m.bobines_palette,
    commandee: 0,
    dejaRecu: 0,
    attendu: 0,
    magasin_id: magasin,
    prix: devise === m.devise ? m.prix_kg : null,
    prixConfirme: false,
    devise,
  }
}

/** Une ligne d'un brouillon à corriger. */
export function depuisFiche(l: LigneReception, devise: string): LigneSaisie {
  return {
    cle: nouvelleCle(),
    commande_ligne_id: l.commande_ligne_id,
    commande_id: l.commande_id,
    commande: l.commande,
    matiere_id: l.matiere_id,
    reference: l.reference,
    designation: l.designation,
    kgParMl: l.kg_par_ml,
    poidsBobine: l.poids_bobine_catalogue,
    bobinesPalette: l.bobines_palette,
    commandee: l.quantite_commandee,
    dejaRecu: l.deja_recu,
    attendu: l.quantite_attendue,
    lot_numero: l.lot_interne ? '' : l.lot_numero,
    lot_interne: l.lot_interne,
    quantite_bl: l.quantite_bl || null,
    quantite_pesee: l.quantite_pesee || null,
    nb_palettes: l.nb_palettes || null,
    bobines_en_plus: l.bobines_en_plus || null,
    magasin_id: l.magasin_id,
    qualite: l.qualite === 'reserve' || l.qualite === 'refuse' ? l.qualite : 'conforme',
    observations: l.observations,
    prix: l.prix || null,
    prixConfirme: l.prix_confirme,
    devise,
  }
}

/** Une ligne qui porte déjà une saisie : la perdre se confirme. */
export const estSaisie = (l: LigneSaisie) =>
  Boolean(
    l.lot_numero.trim() ||
    l.lot_interne ||
    l.quantite_pesee ||
    l.quantite_bl ||
    l.nb_palettes ||
    l.bobines_en_plus,
  )

const n = (v: number | null) => v ?? 0

/** Le refus d'une réception où rien n'est pesé : la même phrase que le serveur. */
export const RIEN_N_EST_PESE =
  "Rien n'est pesé : saisir ce que le camion a apporté (les lignes laissées vides restent dues sur le bon)."

/** Ce qu'il faut d'une ligne (saisie ou lue sur la fiche) pour la dire non livrée. */
export interface LigneRemplie {
  commande_ligne_id: number | null
  commande: string
  qualite: string
  lot_numero: string
  lot_interne: boolean
  quantite_bl: number | null
  quantite_pesee: number | null
  nb_palettes: number | null
  bobines_en_plus: number | null
  nb_bobines?: number | null
}

/**
 * Une ligne de bon, pas refusée, laissée entièrement vide (ni BL, ni pesée, ni palette, ni bobine,
 * ni lot ; les observations ne comptent pas) : ce camion ne l'a pas apportée. Elle ne bloque rien ;
 * la validation la retire, elle reste due sur le bon (règle du serveur, LIVRAISON-PARTIELLE).
 */
export const nonLivree = (l: LigneRemplie) =>
  l.commande_ligne_id != null &&
  l.qualite !== 'refuse' &&
  !l.lot_interne &&
  !l.lot_numero.trim() &&
  !n(l.quantite_bl) &&
  !n(l.quantite_pesee) &&
  !n(l.nb_palettes) &&
  !n(l.bobines_en_plus) &&
  !n(l.nb_bobines ?? null)

/** La note discrète de la saisie : « 3 lignes vides : non livrées par ce camion, … » (vide sans elles). */
export function noteNonLivrees(lignes: readonly LigneRemplie[]): string {
  const vides = lignes.filter(nonLivree).length
  if (!vides) return ''
  return vides === 1
    ? '1 ligne vide : non livrée par ce camion, elle restera due sur le bon.'
    : `${vides} lignes vides : non livrées par ce camion, elles resteront dues sur le bon.`
}

/** Ce que la validation annonce : « 23 lignes non livrées par ce camion seront retirées : … ». */
export function annonceNonLivrees(lignes: readonly LigneRemplie[]): string {
  const vides = lignes.filter(nonLivree)
  if (!vides.length) return ''
  const bons = [...new Set(vides.map((l) => l.commande).filter(Boolean))]
  const sur = bons.length > 1 ? `les bons ${bons.join(', ')}` : `le bon ${bons[0] ?? ''}`
  return vides.length === 1
    ? `1 ligne non livrée par ce camion sera retirée : elle reste due sur ${sur}.`
    : `${vides.length} lignes non livrées par ce camion seront retirées : elles restent dues sur ${sur}.`
}

/** À quoi comparer la pesée : le BL ; sans BL, le reste à livrer, seulement si l'on pèse au moins ce reste. */
export function attenduDe(l: LigneSaisie, tol: Tolerances): number {
  if (n(l.quantite_bl)) return n(l.quantite_bl)
  return l.commande_ligne_id != null && n(l.quantite_pesee) >= l.attendu * (1 - tol.pesee) ? l.attendu : 0
}

/** L'écart de pesée (kg et part), `null` sans attendu ou sans pesée. */
export function ecartDe(
  l: LigneSaisie,
  tol: Tolerances,
): { kg: number; relatif: number; hors: boolean } | null {
  const attendu = attenduDe(l, tol)
  if (!attendu || !n(l.quantite_pesee)) return null
  const kg = n(l.quantite_pesee) - attendu
  const relatif = kg / attendu
  return { kg, relatif, hors: Math.abs(relatif) > tol.pesee }
}

/** Ce que le camion apporte à chaque ligne de bon, tous ses lots ensemble (hors refusé). */
export function apporteParLigne(lignes: readonly LigneSaisie[]): Map<number, number> {
  const m = new Map<number, number>()
  for (const l of lignes)
    if (l.commande_ligne_id != null && l.qualite !== 'refuse')
      m.set(l.commande_ligne_id, (m.get(l.commande_ligne_id) ?? 0) + n(l.quantite_pesee))
  return m
}

/** Vrai si la ligne de bon reçoit plus que son reste + l'excédent toléré (règle du serveur). */
export function enExcedent(l: LigneSaisie, lignes: readonly LigneSaisie[], tol: Tolerances): boolean {
  if (l.commande_ligne_id == null || l.qualite === 'refuse') return false
  const apporte = apporteParLigne(lignes).get(l.commande_ligne_id) ?? 0
  return apporte > Math.max(0, l.commandee - l.dejaRecu) + l.commandee * tol.excedent + 1e-6
}

/** Les bobines de la ligne (palettes × bobines par palette + en plus), le poids moyen et son écart au catalogue. */
export function bobines(l: LigneSaisie): { total: number; moyen: number | null; ecart: number | null } {
  const total = n(l.nb_palettes) * (l.bobinesPalette || 0) + n(l.bobines_en_plus)
  const moyen = total && n(l.quantite_pesee) ? n(l.quantite_pesee) / total : null
  return { total, moyen, ecart: moyen && l.poidsBobine ? moyen / l.poidsBobine - 1 : null }
}

export const devisesDuCamion = (lignes: readonly LigneSaisie[]) =>
  [...new Set(lignes.map((l) => l.devise))].sort()

export function totaux(lignes: readonly LigneSaisie[], tol: Tolerances) {
  return {
    bl: lignes.reduce((s, l) => s + n(l.quantite_bl), 0),
    pese: lignes.filter((l) => l.qualite !== 'refuse').reduce((s, l) => s + n(l.quantite_pesee), 0),
    horsTolerance: lignes.filter((l) => ecartDe(l, tol)?.hors).length,
  }
}

/** Ce que la validation refusera, dit dès la saisie (le serveur reste juge) ; une ligne non livrée n'y compte pas. */
export function blocagesSaisie(
  lignes: readonly LigneSaisie[],
  magasins: readonly Magasin[],
  tol: Tolerances,
): string[] {
  const livrees = lignes.filter((l) => !nonLivree(l))
  if (lignes.length && !livrees.length) return [RIEN_N_EST_PESE]
  const b: string[] = []
  const quarantaine = magasins.some((m) => m.actif && m.type === 'quarantaine')
  for (const l of livrees) {
    if (l.qualite === 'refuse') continue
    if (!n(l.quantite_pesee)) b.push(`« ${l.reference} » : la pesée est à zéro.`)
    if (!l.lot_interne && !l.lot_numero.trim())
      b.push(`« ${l.reference} » : le numéro de lot manque (ou « Lot interne »).`)
    if (l.qualite === 'conforme' && l.magasin_id == null)
      b.push(`« ${l.reference} » : choisir le magasin de rangement.`)
    if (l.qualite === 'reserve' && !quarantaine)
      b.push('Une ligne sous réserve va en quarantaine : créer d’abord un magasin de type « Quarantaine ».')
    if (enExcedent(l, lignes, tol))
      b.push(
        `« ${l.reference} » : excédent au-delà du reste à livrer plus ${arrondi(tol.excedent * 100, 0)} % (tous lots ensemble).`,
      )
  }
  return [...new Set(b)]
}

export interface FactureSaisie {
  numero: string
  date: string
  montant: number | null
  echeance: string
}

export interface EnTete {
  fournisseurId: number
  date: string
  numeroBl: string
  controlePar: string
  observations: string
}

export function corpsLigne(l: LigneSaisie): LigneReceptionEntree {
  return {
    commande_ligne_id: l.commande_ligne_id,
    matiere_id: l.matiere_id,
    lot_numero: l.lot_interne ? '' : l.lot_numero.trim(),
    lot_interne: l.lot_interne,
    quantite_bl: arrondi(n(l.quantite_bl), 3),
    quantite_pesee: arrondi(n(l.quantite_pesee), 3),
    nb_palettes: n(l.nb_palettes),
    bobines_en_plus: n(l.bobines_en_plus),
    magasin_id: l.qualite === 'conforme' ? l.magasin_id : null,
    qualite: l.qualite,
    observations: l.observations.trim(),
    prix: l.prixConfirme || !l.prix ? null : l.prix,
    devise: l.commande_ligne_id ? '' : l.devise,
  }
}

/** Les factures saisies, par devise du camion (une facture sans numéro ne part pas). */
export function corpsFactures(
  factures: Readonly<Record<string, FactureSaisie>>,
  devises: readonly string[],
): Record<string, FactureEntree> {
  const sortie: Record<string, FactureEntree> = {}
  for (const d of devises) {
    const f = factures[d]
    if (!f?.numero.trim()) continue
    sortie[d] = {
      numero: f.numero.trim(),
      date: f.date || null,
      montant: f.montant || null,
      echeance: f.echeance || null,
    }
  }
  return sortie
}

export function corps(
  e: EnTete,
  lignes: readonly LigneSaisie[],
  factures: Readonly<Record<string, FactureSaisie>>,
): ReceptionCreation {
  return {
    date: e.date,
    fournisseur_id: e.fournisseurId,
    numero_bl: e.numeroBl.trim(),
    controle_par: e.controlePar.trim(),
    observations: e.observations.trim(),
    factures: corpsFactures(factures, devisesDuCamion(lignes)),
    lignes: lignes.map(corpsLigne),
  }
}
