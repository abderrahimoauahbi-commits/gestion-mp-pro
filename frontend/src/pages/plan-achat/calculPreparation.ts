/**
 * La préparation d'une commande, sans écran (ECRANS-PRO 4.4) : le calcul suggère, l'acheteur
 * arbitre. Chaque ligne se saisit dans l'unité où l'on commande vraiment (kilo, bobine, palette,
 * fût…) **et** en kilos, les deux liés ; le serveur reçoit des kilos, l'unité et sa contenance.
 * Les règles de départ sont celles du serveur (`ligne.depart`) ; une matière ajoutée part d'une
 * unité entière (ou de son minimum au kilo).
 */
import { arrondi } from '../../lib/format'
import type { Ton } from '../../lib/statuts'
import { bonsEnPreparation } from './libelles'
import type { CommandeCreation, Devise, LignePreparation, Matiere, UniteCommande } from './types'

export interface LigneSaisie {
  matiere_id: number
  reference: string
  designation: string
  nature: string
  devise: string
  /** Vide pour une ligne ajoutée à la main : le calcul ne la demandait pas. */
  statut: string
  classe_abc: string
  couverture_jours: number | null
  stock_projete: number | null
  conso_mensuelle: number | null
  /** La suggestion du calcul, en kilos, et dans l'unité de commande du calcul. */
  suggestion: number
  suggestion_unites: number
  suggestion_unite: string
  minimum: number
  contenance_palette: number
  /** Le prix du catalogue au kilo, dans la devise de la matière (0 : pas de prix). */
  prix: number
  unites: UniteCommande[]
  unite: string
  contenance: number
  kgParMl: number
  /** « déjà en préparation : 300 kg (Brouillon) » : déduit de la suggestion. */
  enPreparation: string
  /** En kilos : c'est ce que le serveur enregistre. */
  quantite: number
  retenue: boolean
  ajoutee: boolean
}

/** La ligne telle que la préparation la propose d'abord (unité, kilos : `depart` du serveur). */
export function depuisServeur(l: LignePreparation): LigneSaisie {
  const unites = l.unites_possibles.length ? l.unites_possibles : [{ unite: 'kg', contenance: 1 }]
  return {
    matiere_id: l.matiere_id ?? 0,
    reference: l.reference,
    designation: l.designation,
    nature: l.nature,
    devise: l.devise,
    statut: l.statut,
    classe_abc: l.classe_abc,
    couverture_jours: l.couverture_jours,
    stock_projete: l.stock_projete,
    conso_mensuelle: l.conso_mensuelle,
    suggestion: l.depart.quantite,
    suggestion_unites: l.unites_suggerees,
    suggestion_unite: l.unite_commande,
    minimum: l.minimum_commande,
    contenance_palette: l.contenance_palette,
    prix: l.prix_indicatif,
    unites,
    unite: l.depart.unite,
    contenance: l.depart.contenance || 1,
    kgParMl: l.kg_par_ml,
    enPreparation: l.en_preparation
      ? `déjà en préparation : ${arrondi(l.en_preparation, 0)} kg (${bonsEnPreparation(l.bons_en_preparation)}), déduits`
      : '',
    quantite: l.depart.quantite,
    retenue: true,
    ajoutee: false,
  }
}

/** Les conditionnements où une matière se commande (règle du serveur, jamais « ml »). */
export function unitesDe(m: Matiere): UniteCommande[] {
  const u: UniteCommande[] = [{ unite: 'kg', contenance: 1 }]
  if (m.poids_bobine > 0) u.push({ unite: 'Bobine', contenance: m.poids_bobine })
  if (m.poids_bobine > 0 && m.bobines_palette > 0)
    u.push({ unite: 'Palette', contenance: arrondi(m.poids_bobine * m.bobines_palette, 6) })
  if (m.unite_achat && !['kg', 'ml'].includes(m.unite_achat) && m.contenance_achat > 0)
    u.push({ unite: m.unite_achat, contenance: m.contenance_achat })
  return u
}

/** Une matière ajoutée à la main : une unité entière (la dernière permise), ou son minimum au kilo. */
export function depuisMatiere(m: Matiere): LigneSaisie {
  const unites = unitesDe(m)
  const choisie = unites[unites.length - 1] ?? { unite: 'kg', contenance: 1 }
  return {
    matiere_id: m.id,
    reference: m.reference,
    designation: m.designation,
    nature: m.role,
    devise: m.devise ?? 'MAD',
    statut: '',
    classe_abc: '',
    couverture_jours: null,
    stock_projete: null,
    conso_mensuelle: null,
    suggestion: 0,
    suggestion_unites: 0,
    suggestion_unite: '',
    minimum: m.minimum_commande ?? 0,
    contenance_palette: m.contenance_palette,
    prix: m.prix_kg ?? 0,
    unites,
    unite: choisie.unite,
    contenance: choisie.contenance || 1,
    kgParMl: m.kg_par_ml,
    enPreparation: '',
    quantite: choisie.contenance > 1 ? choisie.contenance : Math.max(m.minimum_commande ?? 0, 0),
    retenue: true,
    ajoutee: true,
  }
}

/** Les lignes qui partiront sur le bon : cochées, avec une quantité. */
export const retenues = (lignes: readonly LigneSaisie[]) => lignes.filter((l) => l.retenue && l.quantite > 0)

export interface Totaux {
  kilos: number
  palettes: number
  parDevise: Record<string, number>
  /** Au cours du jour ; `null` si une devise n'a pas de cours connu. */
  mad: number | null
}

export function totaux(lignes: readonly LigneSaisie[], devises: readonly Devise[]): Totaux {
  const cours = new Map(devises.map((d) => [d.code, d.cours]))
  const parDevise: Record<string, number> = {}
  let palettes = 0
  let kilos = 0
  for (const l of retenues(lignes)) {
    kilos += l.quantite
    if (l.contenance_palette) palettes += l.quantite / l.contenance_palette
    if (l.prix) parDevise[l.devise] = (parDevise[l.devise] ?? 0) + l.quantite * l.prix
  }
  let mad: number | null = 0
  for (const [d, v] of Object.entries(parDevise)) {
    const c = d === 'MAD' ? 1 : cours.get(d)
    mad = mad == null || c == null ? null : mad + v * c
  }
  return { kilos, palettes, parDevise, mad }
}

/** Les devises des lignes retenues : un bon par devise. */
export const devisesDe = (lignes: readonly LigneSaisie[]) =>
  [...new Set(retenues(lignes).map((l) => l.devise))].sort()

/** La place restante dans le dernier conteneur (palettes), 0 sans réglage ou s'il est plein. */
export function placeRestante(
  palettes: number,
  parConteneur: number | null,
): { conteneurs: number | null; libres: number } {
  if (!parConteneur || parConteneur <= 0) return { conteneurs: null, libres: 0 }
  const conteneurs = palettes / parConteneur
  const libres = conteneurs > 0 ? Math.ceil(conteneurs - 1e-9) * parConteneur - palettes : 0
  return { conteneurs, libres }
}

export type Ecart =
  | { genre: 'non_commandee' }
  | { genre: 'hors_calcul' }
  | { genre: 'aucun' }
  | { genre: 'suggestion' }
  | { genre: 'ecart'; valeur: number; ton: Ton }

/** Ce qu'on commande face à la suggestion : ok ≤ 10 %, attention au-dessus, critique en dessous. */
export function ecart(l: LigneSaisie): Ecart {
  if (!l.retenue) return { genre: 'non_commandee' }
  if (l.ajoutee) return { genre: 'hors_calcul' }
  if (!l.suggestion) return { genre: 'aucun' }
  const e = l.quantite / l.suggestion - 1
  if (Math.abs(e) < 0.005) return { genre: 'suggestion' }
  return { genre: 'ecart', valeur: e, ton: Math.abs(e) <= 0.1 ? 'ok' : e > 0 ? 'attention' : 'critique' }
}

/** L'avertissement de la ligne (non bloquant) : sous le minimum, ou unité entamée. */
export function avertissement(l: LigneSaisie): string {
  if (l.retenue && l.minimum > 0 && l.quantite > 0 && l.quantite < l.minimum)
    return `sous le minimum (${arrondi(l.minimum, 1)} kg)`
  const unites = l.quantite / (l.contenance || 1)
  if (l.contenance > 1 && Math.abs(unites - Math.round(unites)) > 0.001)
    return `${l.unite.toLowerCase()} entamée`
  return ''
}

/** « Arrondir au conditionnement » : chaque quantité monte à l'unité entière suivante. */
export function arrondirAuConditionnement(lignes: readonly LigneSaisie[]): LigneSaisie[] {
  return lignes.map((l) =>
    l.contenance > 1 && l.quantite > 0
      ? { ...l, quantite: arrondi(Math.ceil(l.quantite / l.contenance - 1e-9) * l.contenance, 3) }
      : l,
  )
}

/** « Revenir à la suggestion » : les quantités calculées, sans les lignes ajoutées. */
export function revenirALaSuggestion(depart: readonly LigneSaisie[]): LigneSaisie[] {
  return depart.filter((l) => !l.ajoutee).map((l) => ({ ...l }))
}

/** Changer d'unité garde les kilos. */
export function changerUnite(l: LigneSaisie, unite: string): LigneSaisie {
  const u = l.unites.find((x) => x.unite === unite)
  return u ? { ...l, unite: u.unite, contenance: u.contenance || 1 } : l
}

export interface Entete {
  fournisseurId: number
  livraison: string
  observations: string
  prixCatalogue: boolean
}

/** Le corps de `POST /commandes` : les lignes retenues, en kilos au gramme. */
export function corps(e: Entete, lignes: readonly LigneSaisie[]): CommandeCreation {
  return {
    fournisseur_id: e.fournisseurId,
    date_livraison_prevue: e.livraison || null,
    prix_catalogue_a_confirmer: e.prixCatalogue,
    observations: e.observations.trim(),
    lignes: retenues(lignes).map((l) => ({
      matiere_id: l.matiere_id,
      quantite: arrondi(l.quantite, 3),
      unite_achat: l.unite,
      contenance: l.contenance || 1,
    })),
  }
}
