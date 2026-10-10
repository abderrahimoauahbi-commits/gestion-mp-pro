/**
 * Le comptage d'un inventaire, sans écran (ECRANS-PRO partie 6, « Comptage ») : la ligne telle
 * qu'elle est à l'écran (le brouillon local par-dessus ce que sait le serveur), les vues, les
 * totaux, ce que « Valider » attend, et le corps de `PUT inventaires/{id}/comptages`.
 *
 * Une ligne **enregistrée** se lit au serveur (`retenu`, `hors_tolerance`, `a_recompter`,
 * `quatre_yeux`, an. 15) ; seule une ligne **modifiée localement** se recalcule ici, avec les
 * règles du serveur (seuil 0,001 kg ; théorique nul et compté > 0 : hors tolérance ; le recompté,
 * s'il existe, est retenu ; justification de 3 caractères au moins).
 */
import { nombre, nombreSigne } from '../../lib/format'
import { POUSSIERE, type InventaireFiche, type LigneInventaire } from './types'

/** La justification la plus courte (écran et serveur). */
export const JUSTIFICATION_MINIMUM = 3

export interface Brouillon {
  compte: number | null
  palettes: number | null
  bobines: number | null
  second_compte: number | null
  justification: string
}

export type Brouillons = Readonly<Record<number, Brouillon>>

export type Vue = 'toutes' | 'a_compter' | 'comptees' | 'ecarts' | 'hors' | 'recompter' | 'modifiees'

export interface EtatLigne {
  ligne: LigneInventaire
  modifiee: boolean
  compte: number | null
  palettes: number | null
  bobines: number | null
  second: number | null
  justification: string
  retenu: number | null
  ecart: number | null
  hors: boolean
  recompter: boolean
  /** Hors tolérance sans justification suffisante (ligne en rouge). */
  manque: boolean
  valeur: number | null
  /** Le recomptage fait par la même personne (signalé, jamais refusé). */
  quatreYeux: string
}

/** Hors tolérance : compté, écart d'au moins 0,001 kg, et théorique nul ou écart relatif au-delà. */
export function horsTolerance(theorique: number, retenu: number | null, tolerance: number): boolean {
  if (retenu == null) return false
  const ecart = retenu - theorique
  if (Math.abs(ecart) < POUSSIERE) return false
  if (theorique <= 0) return true
  return Math.abs(ecart) / theorique > tolerance
}

/** Qui recompte : la personne connectée, comparée au premier compteur et à l'ouvreur. */
export interface Recompteur {
  nom: string
  ouvreur: string
}

const MEME_PREMIER = 'même personne que le premier comptage : un recomptage se fait à quatre yeux'
const MEME_OUVREUR = "même personne que l'ouvreur : un recomptage se fait à quatre yeux"

/** Le signalement d'un recomptage saisi ici et pas encore enregistré. */
function quatreYeuxLocal(l: LigneInventaire, b: Brouillon, qui: Recompteur): string {
  if (b.second_compte == null || b.second_compte === l.second_compte) return l.quatre_yeux
  const premier = b.compte !== l.compte || !l.compte_par ? qui.nom : l.compte_par
  if (premier === qui.nom) return MEME_PREMIER
  return qui.ouvreur === qui.nom ? MEME_OUVREUR : ''
}

/** La ligne à l'écran : lue au serveur si elle n'est pas modifiée, recalculée sinon. */
export function etatLigne(
  l: LigneInventaire,
  b: Brouillon | undefined,
  tolerance: number,
  qui: Recompteur,
): EtatLigne {
  if (!b) {
    const manque = l.hors_tolerance && l.justification.trim().length < JUSTIFICATION_MINIMUM
    return {
      ligne: l,
      modifiee: false,
      compte: l.compte,
      palettes: l.palettes,
      bobines: l.bobines,
      second: l.second_compte,
      justification: l.justification,
      retenu: l.retenu,
      ecart: l.ecart,
      hors: l.hors_tolerance,
      recompter: l.a_recompter,
      manque,
      valeur: l.valeur_ecart_mad,
      quatreYeux: l.quatre_yeux,
    }
  }
  const retenu = b.second_compte ?? b.compte
  const ecart = retenu == null ? null : retenu - l.theorique
  const hors = horsTolerance(l.theorique, retenu, tolerance)
  return {
    ligne: l,
    modifiee: true,
    compte: b.compte,
    palettes: b.palettes,
    bobines: b.bobines,
    second: b.second_compte,
    justification: b.justification,
    retenu,
    ecart,
    hors,
    recompter: b.second_compte == null && horsTolerance(l.theorique, b.compte, tolerance),
    manque: hors && b.justification.trim().length < JUSTIFICATION_MINIMUM,
    valeur: ecart == null || l.cmup_mad == null ? null : ecart * l.cmup_mad,
    quatreYeux: quatreYeuxLocal(l, b, qui),
  }
}

/** Le brouillon d'une ligne à partir de ce que sait le serveur. */
export function brouillonDe(l: LigneInventaire): Brouillon {
  return {
    compte: l.compte,
    palettes: l.palettes,
    bobines: l.bobines,
    second_compte: l.second_compte,
    justification: l.justification,
  }
}

const memeQueServeur = (l: LigneInventaire, b: Brouillon) =>
  b.compte === l.compte &&
  b.second_compte === l.second_compte &&
  b.justification === l.justification &&
  b.palettes === l.palettes &&
  b.bobines === l.bobines

/**
 * Une saisie de cellule : palettes et bobines donnent le poids (palettes × bobines par palette
 * + bobines, × poids de bobine du lot, arrondi au centième) ; saisir le compté efface palettes et
 * bobines. Revenue à ce que sait le serveur, la ligne n'est plus à enregistrer.
 */
export function changer(brouillons: Brouillons, l: LigneInventaire, modif: Partial<Brouillon>): Brouillons {
  const avant = brouillons[l.id] ?? brouillonDe(l)
  const suivant = { ...avant, ...modif }
  if (('palettes' in modif || 'bobines' in modif) && l.poids_bobine > 0) {
    const vides = suivant.palettes == null && suivant.bobines == null
    const nb = (suivant.palettes ?? 0) * (l.bobines_palette || 0) + (suivant.bobines ?? 0)
    suivant.compte = vides ? avant.compte : Math.round(nb * l.poids_bobine * 100) / 100
  }
  if ('compte' in modif) {
    suivant.palettes = null
    suivant.bobines = null
  }
  const reste = Object.fromEntries(Object.entries(brouillons).filter(([cle]) => Number(cle) !== l.id))
  return memeQueServeur(l, suivant) ? reste : { ...reste, [l.id]: suivant }
}

/** Les saisies qui restent après un envoi : celles modifiées depuis (tapées pendant l'envoi). */
export function sansLesEnvoyes(actuels: Brouillons, envoyes: Brouillons): Brouillons {
  return Object.fromEntries(Object.entries(actuels).filter(([cle, b]) => envoyes[Number(cle)] !== b))
}

/** Les lignes d'une vue. */
export function dansLaVue(e: EtatLigne, vue: Vue): boolean {
  switch (vue) {
    case 'a_compter':
      return e.compte == null
    case 'comptees':
      return e.compte != null
    case 'ecarts':
      return e.ecart != null && Math.abs(e.ecart) >= POUSSIERE
    case 'hors':
      return e.hors
    case 'recompter':
      return e.recompter
    case 'modifiees':
      return e.modifiee
    default:
      return true
  }
}

export const VUES: readonly { cle: Vue; libelle: string }[] = [
  { cle: 'toutes', libelle: 'Tous les lots' },
  { cle: 'a_compter', libelle: 'À compter' },
  { cle: 'comptees', libelle: 'Comptés' },
  { cle: 'ecarts', libelle: 'Avec un écart' },
  { cle: 'hors', libelle: 'Hors tolérance' },
  { cle: 'recompter', libelle: 'À recompter' },
  { cle: 'modifiees', libelle: 'Non enregistrés' },
]

export interface Totaux {
  lignes: number
  comptees: number
  hors: number
  sansJustification: number
  aRecompter: number
  recomptees: number
  memePersonne: number
  ajustes: number
  modifiees: number
  ecart: number
  valeur: number
  valeurAbsolue: number
}

/** Les totaux de la fiche (indicateurs, confirmation de validation). */
export function totaux(etats: readonly EtatLigne[]): Totaux {
  const t: Totaux = {
    lignes: etats.length,
    comptees: 0,
    hors: 0,
    sansJustification: 0,
    aRecompter: 0,
    recomptees: 0,
    memePersonne: 0,
    ajustes: 0,
    modifiees: 0,
    ecart: 0,
    valeur: 0,
    valeurAbsolue: 0,
  }
  for (const e of etats) {
    if (e.modifiee) t.modifiees += 1
    if (e.hors) t.hors += 1
    if (e.manque) t.sansJustification += 1
    if (e.recompter) t.aRecompter += 1
    if (e.second != null) t.recomptees += 1
    if (e.quatreYeux) t.memePersonne += 1
    if (e.compte == null) continue
    t.comptees += 1
    t.ecart += e.ecart ?? 0
    t.valeur += e.valeur ?? 0
    t.valeurAbsolue += Math.abs(e.valeur ?? 0)
    if (Math.abs(e.ecart ?? 0) >= POUSSIERE) t.ajustes += 1
  }
  return t
}

/** Les comptages à envoyer : les lignes modifiées seulement. */
export function corpsComptages(fiche: InventaireFiche, brouillons: Brouillons) {
  return {
    version: fiche.version,
    lignes: Object.entries(brouillons).map(([ligne, b]) => ({
      ligne_id: Number(ligne),
      compte: b.compte,
      palettes: b.palettes,
      bobines: b.bobines,
      second_compte: b.second_compte,
      justification: b.justification.trim(),
    })),
  }
}

const BLOCAGES_RECALCULES = [/^Aucun lot compté/, /^Écart hors tolérance sans justification/]

/**
 * Ce qui grise « Valider » : les blocages du serveur tels quels si rien n'est modifié ; sinon ceux
 * qui ne dépendent pas de la saisie, plus ce que la saisie locale laisse en manque.
 */
export function raisonsDeValider(fiche: InventaireFiche, t: Totaux): string[] {
  if (!t.modifiees) return fiche.blocages
  const raisons: string[] = []
  if (t.sansJustification)
    raisons.push(
      `${nombre(t.sansJustification)} écart(s) hors tolérance sans justification : écrire d’abord ce qui a été constaté (lignes en rouge)`,
    )
  if (!t.comptees) raisons.push('Aucun lot compté')
  return [...raisons, ...fiche.blocages.filter((b) => !BLOCAGES_RECALCULES.some((r) => r.test(b)))]
}

/** La question de « Valider l'inventaire ». */
export function questionValider(t: Totaux): string {
  const morceaux = [
    `${nombre(t.comptees)} lot(s) comptés`,
    `${nombre(t.ajustes)} écart(s) ajusté(s) (${nombreSigne(t.ecart, 0, 2)} kg)`,
  ]
  const nonComptes = t.lignes - t.comptees
  if (nonComptes) morceaux.push(`${nombre(nonComptes)} non comptés restent au théorique`)
  if (t.memePersonne) morceaux.push(`${nombre(t.memePersonne)} recomptage(s) faits par la même personne`)
  return `Valider ? ${morceaux.join(', ')}. Seule une annulation (contre-passation, avec un motif) la défait.`
}
