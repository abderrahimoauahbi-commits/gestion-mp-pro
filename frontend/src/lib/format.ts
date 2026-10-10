/**
 * La règle unique d'arrondi et d'affichage (ARCHITECTURE § 9.3) : une fonction par grandeur.
 *
 * Les gabarits imprimés (`documents/rendu.py`) et les classeurs Excel (`exports/classeur.py`)
 * reprennent exactement ces règles ; un écart entre eux est une anomalie.
 *
 * - Arrondi : ARRONDI d'Excel (demi loin de zéro), une seule fois, sur la valeur brute, à
 *   l'écriture décimale la plus courte du nombre (2,675 → 2,68 comme Excel et `Decimal(str(v))`).
 * - Milliers : espace insécable U+00A0 (visible, ne coupe pas) ; décimales : virgule ;
 *   négatif : « − » (U+2212). Jamais « -0 », « −0,0 % » : un nombre qui s'arrondit à zéro n'a pas
 *   de signe.
 * - Vide (`null`, `undefined`, NaN, infini) : « — ».
 *
 * Aucune dépendance à `Intl` : le même texte sur tous les navigateurs, au téléphone et en essai.
 */

import { decouper, instantDe, instantServeur, joursDepuis, murDe, type Mur } from './heure'

/** Ce qu'on affiche quand il n'y a rien. */
export const VIDE = '—'
/** L'espace insécable des milliers et entre un nombre et son unité. */
export const INSECABLE = ' '
/** Le signe moins typographique. */
export const MOINS = '−'

type Valeur = number | null | undefined

/** Un nombre qu'on peut afficher (ni vide, ni NaN, ni infini). */
export function estAffichable(valeur: Valeur): valeur is number {
  return typeof valeur === 'number' && Number.isFinite(valeur)
}

/** Multiplie par 10^d sur l'écriture décimale du nombre (pas d'erreur de flottant : 1,005 × 100 = 100,5). */
function decaler(valeur: number, d: number): number {
  const [mantisse, exposant = '0'] = String(valeur).split('e')
  return Number(`${mantisse}e${Number(exposant) + d}`)
}

/** ARRONDI d'Excel : le demi s'éloigne de zéro (2,5 → 3 ; −2,5 → −3 ; 2,675 à 2 déc. → 2,68). */
export function arrondi(valeur: number, decimales = 0): number {
  if (!Number.isFinite(valeur)) return valeur
  const r = decaler(Math.round(decaler(Math.abs(valeur), decimales)), -decimales)
  return r === 0 ? 0 : valeur < 0 ? -r : r
}

/**
 * Le nombre écrit à la française : `decimales` exactes, et jusqu'à `decimalesMax` quand il en faut
 * (les zéros au-delà de `decimales` ne s'écrivent pas). « 17 398 184 » ; « 1 234,5 » ; « −3 ».
 */
export function nombre(valeur: Valeur, decimales = 0, decimalesMax = decimales): string {
  if (!estAffichable(valeur)) return VIDE
  const max = Math.max(decimales, decimalesMax)
  const r = arrondi(valeur, max)
  const absolu = Math.abs(r)
  const [entier = '0', fraction = ''] = (absolu >= 1e21 ? String(absolu) : absolu.toFixed(max)).split('.')
  const gardees = fraction.slice(0, decimales) + fraction.slice(decimales).replace(/0+$/, '')
  const groupes = entier.replace(/\B(?=(\d{3})+(?!\d))/g, INSECABLE)
  const texte = gardees ? `${groupes},${gardees}` : groupes
  return r < 0 ? `${MOINS}${texte}` : texte
}

/** Un écart se lit avec son signe : « +12,5 », « −3,0 », « 0,0 » (zéro sans signe). Comme
 * `nombre`, `decimalesMax` autorise des décimales supplémentaires, zéros au-delà non écrits. */
export function nombreSigne(valeur: Valeur, decimales = 0, decimalesMax = decimales): string {
  if (!estAffichable(valeur)) return VIDE
  const texte = nombre(valeur, decimales, decimalesMax)
  return arrondi(valeur, Math.max(decimales, decimalesMax)) > 0 ? `+${texte}` : texte
}

const avecUnite = (texte: string, unite: string) => (texte === VIDE ? VIDE : `${texte}${INSECABLE}${unite}`)

// ─── Kilos et mètres ──────────────────────────────────────────────────────────────────────────

/** Kilos au bureau : jusqu'à deux décimales, zéros inutiles enlevés (« 3,15 kg », « 52,4 kg »,
 * « 26 000 kg ») ; Excel `#,##0.##`. */
export function kg(valeur: Valeur): string {
  return avecUnite(nombre(valeur, 0, 2), 'kg')
}

/** Les décimales des kilos au téléphone : entier dès 100 kg, une de 10 à 100, deux sous 10. */
export function decimalesTelephone(valeur: number): number {
  const absolu = Math.abs(valeur)
  if (absolu >= 100 || Math.abs(arrondi(valeur, 1)) >= 100) return 0
  if (absolu >= 10 || Math.abs(arrondi(valeur, 2)) >= 10) return 1
  return 2
}

/** Kilos au téléphone : « 445 kg », « 52,4 kg », « 2,49 kg ». */
export function kgTelephone(valeur: Valeur): string {
  if (!estAffichable(valeur)) return VIDE
  return avecUnite(nombre(valeur, decimalesTelephone(valeur)), 'kg')
}

/** Kilos commandés au kilo : entiers (« 5 029 kg »). */
export function kgEntier(valeur: Valeur): string {
  return avecUnite(nombre(valeur, 0), 'kg')
}

/**
 * Les mètres d'un poids, à titre indicatif, pour un cuir, des franges, un ruban (`kgParMl` : leur
 * densité) : « ≈ 1 020 ml ». Vide pour une matière au poids, sans densité, ou quand l'arrondi
 * donnerait « ≈ 0 ml ». Le stock, lui, est toujours en kilos.
 */
export function metres(kilos: Valeur, kgParMl: Valeur): string {
  if (!estAffichable(kilos) || !estAffichable(kgParMl) || kgParMl <= 0) return ''
  const ml = arrondi(kilos / kgParMl, 0)
  return ml === 0 ? '' : `≈${INSECABLE}${nombre(ml)}${INSECABLE}ml`
}

/** « 14,3 kg », et « 14,3 kg ≈ 1 020 ml » pour un cuir, des franges, un ruban. */
export function kgEtMetres(kilos: Valeur, kgParMl?: Valeur, telephone = false): string {
  if (!estAffichable(kilos)) return VIDE
  const m = metres(kilos, kgParMl)
  const k = telephone ? kgTelephone(kilos) : kg(kilos)
  return m ? `${k} ${m}` : k
}

/** Poids d'une bobine : jusqu'à deux décimales, sans zéros (« 3,15 kg / bobine », « 2,5 kg / bobine »). */
export function poidsBobine(valeur: Valeur): string {
  if (!estAffichable(valeur)) return VIDE
  return `${nombre(valeur, 0, 2)}${INSECABLE}kg / bobine`
}

/** Surface : entière (« 1 200 m² »). */
export function m2(valeur: Valeur): string {
  return avecUnite(nombre(valeur, 0), 'm²')
}

/** Une durée en jours (« 45 j »). */
export function jours(valeur: Valeur): string {
  return avecUnite(nombre(valeur, 0), 'j')
}

// ─── Argent ───────────────────────────────────────────────────────────────────────────────────

/** Montant des tableaux et indicateurs : entier, devise toujours dite (« 1 234 MAD »). */
export function montant(valeur: Valeur, devise: string): string {
  return avecUnite(nombre(valeur, 0), devise)
}

/** Montant des documents, de l'échéancier, des dossiers, et des infobulles : au centime. */
export function montantPrecis(valeur: Valeur, devise: string): string {
  return avecUnite(nombre(valeur, 2), devise)
}

/** Indicateur : « 17,4 M MAD » à partir d'un million (le montant exact va en infobulle). */
export function montantCourt(valeur: Valeur, devise: string): string {
  if (!estAffichable(valeur)) return VIDE
  if (Math.abs(arrondi(valeur, 0)) < 1_000_000) return montant(valeur, devise)
  return `${nombre(valeur / 1_000_000, 1)}${INSECABLE}M${INSECABLE}${devise}`
}

/** Plusieurs devises ne s'additionnent jamais : « 61 888 USD · 53 132 EUR » (du plus gros au plus petit). */
export function montants(parDevise: Record<string, number> | null | undefined, precis = false): string {
  const entrees = Object.entries(parDevise ?? {}).filter(([, v]) => estAffichable(v) && arrondi(v, 2) !== 0)
  if (!entrees.length) return VIDE
  return entrees
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([devise, v]) => (precis ? montantPrecis(v, devise) : montant(v, devise)))
    .join(' · ')
}

/** Un prix unitaire : deux décimales, jusqu'à quatre sous 0,1 (un mètre à 0,0011 ne devient pas 0,00). */
export function prix(valeur: Valeur): string {
  if (!estAffichable(valeur)) return VIDE
  return valeur !== 0 && Math.abs(valeur) < 0.1 ? nombre(valeur, 2, 4) : nombre(valeur, 2)
}

/** Un prix avec sa devise et son unité : « 2,80 USD / kg », « 0,0011 USD / ml ». */
export function prixUnite(valeur: Valeur, devise: string, unite: string): string {
  const texte = prix(valeur)
  return texte === VIDE ? VIDE : `${texte}${INSECABLE}${devise} / ${unite}`
}

/** Un cours de change : quatre décimales (« 10,0500 »). */
export function cours(valeur: Valeur): string {
  return nombre(valeur, 4)
}

// ─── Parts ────────────────────────────────────────────────────────────────────────────────────

/** Un pourcentage déjà exprimé en % : « 12,5 % ». */
export function pourcent(valeur: Valeur, decimales = 1): string {
  return avecUnite(nombre(valeur, decimales), '%')
}

/** Une fraction (0,125) dite en pourcentage : « 12,5 % ». */
export function part(valeur: Valeur, decimales = 1): string {
  return estAffichable(valeur) ? pourcent(decaler(valeur, 2), decimales) : VIDE
}

/** Une évolution se lit avec son signe : « +4,2 % », « −1,0 % », « 0,0 % ». */
export function partSignee(valeur: Valeur, decimales = 1): string {
  return estAffichable(valeur) ? avecUnite(nombreSigne(decaler(valeur, 2), decimales), '%') : VIDE
}

/** Le classement d'un fournisseur dit dans le vocabulaire du score : « À surveiller » → ATTENTION
 * (repris de Gestion MP ; les deux noms restent signalés à Mohamed, ECRANS-PRO § 5 E7). */
export function classementLisible(classement: string): string {
  return classement.replace('À surveiller', 'ATTENTION')
}

// ─── Dates (heure de l'usine, lib/heure.ts) ───────────────────────────────────────────────────

const MOIS = [
  'janvier',
  'février',
  'mars',
  'avril',
  'mai',
  'juin',
  'juillet',
  'août',
  'septembre',
  'octobre',
  'novembre',
  'décembre',
]
const MOIS_COURTS = [
  'janv.',
  'févr.',
  'mars',
  'avr.',
  'mai',
  'juin',
  'juil.',
  'août',
  'sept.',
  'oct.',
  'nov.',
  'déc.',
]

const deux = (n: number) => String(Math.floor(n)).padStart(2, '0')
const jjmmaaaa = (m: Mur) => `${deux(m.jour)}/${deux(m.mois)}/${m.annee}`
const jjmmaaaaIso = (m: Mur) => `${m.annee}-${deux(m.mois)}-${deux(m.jour)}`
const hhmm = (m: Mur) => `${deux(m.heure)}:${deux(m.minute)}`

/** Une date : « 08/10/2026 » (une date seule est un jour du calendrier de l'usine, jamais minuit UTC). */
export function date(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = murDe(valeur)
  return lu ? jjmmaaaa(lu.mur) : valeur
}

/** Un horodatage : « 08/10/2026 14:05 », à l'heure de l'usine. */
export function horodatage(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = murDe(valeur)
  if (!lu) return valeur
  return lu.avecHeure ? `${jjmmaaaa(lu.mur)} ${hhmm(lu.mur)}` : jjmmaaaa(lu.mur)
}

/** Le jour, dit « aujourd'hui » ou « hier » selon l'heure du serveur, sinon « 08/10/2026 ». */
export function jourRelatif(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = murDe(valeur)
  if (!lu) return valeur
  const ecart = joursDepuis(jjmmaaaaIso(lu.mur))
  if (ecart === 0) return "aujourd'hui"
  if (ecart === 1) return 'hier'
  return jjmmaaaa(lu.mur)
}

/** « aujourd'hui 14:05 », « hier 09:12 », sinon « 08/10/2026 14:05 ». */
export function horodatageRelatif(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = murDe(valeur)
  if (!lu) return valeur
  const jour = jourRelatif(valeur)
  return lu.avecHeure ? `${jour} ${hhmm(lu.mur)}` : jour
}

/** Depuis quand, à l'heure du serveur : « à l'instant », « il y a 40 min », « il y a 3 h », « il y a 2 j ». */
export function ilYa(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const instant = instantDe(valeur)
  if (instant == null) return valeur
  const minutes = Math.floor((instantServeur() - instant) / 60_000)
  if (minutes < 1) return "à l'instant"
  if (minutes < 60) return `il y a ${minutes}${INSECABLE}min`
  if (minutes < 24 * 60) return `il y a ${Math.floor(minutes / 60)}${INSECABLE}h`
  if (minutes < 7 * 24 * 60) return `il y a ${Math.floor(minutes / 1440)}${INSECABLE}j`
  return date(valeur)
}

/** Un mois : « octobre 2026 » (« 2026-10 » ou une date du mois). */
export function mois(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = decouper(valeur.length === 7 ? `${valeur}-01` : valeur)
  return lu ? `${MOIS[lu.mur.mois - 1]} ${lu.mur.annee}` : valeur
}

/** Un mois en abrégé : « oct. 2026 ». */
export function moisCourt(valeur: string | null | undefined): string {
  if (!valeur) return VIDE
  const lu = decouper(valeur.length === 7 ? `${valeur}-01` : valeur)
  return lu ? `${MOIS_COURTS[lu.mur.mois - 1]} ${lu.mur.annee}` : valeur
}
