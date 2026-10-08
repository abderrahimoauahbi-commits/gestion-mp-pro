/**
 * L'heure de l'usine, c'est-à-dire celle du serveur — jamais celle du poste (REGLES-ECRAN § 3).
 *
 * Un navigateur peut compter un autre fuseau que le serveur (en octobre 2026, Chrome comptait le
 * Maroc à +01 quand le Mac de l'usine était à +00), ou une horloge mal réglée. Chaque réponse du
 * serveur porte son heure dans l'en-tête `X-Heure-Serveur` ; `lib/api.ts` la passe à
 * `recalerHorloge`, et toute « date du jour » de l'écran se lit ici.
 *
 * Deux grandeurs sont tenues :
 * - l'**heure murale** de l'usine (jour, heure, minute affichés à Casablanca), gardée comme un
 *   décalage avec `Date.now()` et lue en champs UTC : aucun fuseau du navigateur n'intervient ;
 * - l'**instant** du serveur, quand l'en-tête porte son décalage (« 2026-10-08T13:20:46+01:00 ») :
 *   il sert aux durées (« il y a 40 min ») et à présenter les instants à l'heure de l'usine.
 *
 * Formes acceptées de l'en-tête : « AAAA-MM-JJTHH:MM:SS » (heure murale, comme Gestion MP),
 * suivie au besoin de fractions de seconde et d'un décalage « Z », « +01:00 », « +0100 ».
 */

/** Les champs d'une heure murale (mois de 1 à 12). */
export interface Mur {
  annee: number
  mois: number
  jour: number
  heure: number
  minute: number
  seconde: number
}

const MINUTE = 60_000
const JOUR = 86_400_000

const MOTIF =
  /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?)?\s*(Z|[+-]\d{2}(?::?\d{2})?)?$/

/** Avant toute réponse du serveur : l'heure murale du poste (seule connue). */
const decalageDuPoste = () => -new Date().getTimezoneOffset() * MINUTE

let decalageMur = decalageDuPoste()
let decalageInstant: number | null = null
let decalageUsine: number | null = null

/** Le décalage (en minutes) d'un suffixe « Z », « +01:00 », « -0330 ». */
function minutesDuDecalage(texte: string): number {
  if (texte === 'Z') return 0
  const signe = texte.startsWith('-') ? -1 : 1
  const chiffres = texte.slice(1).replace(':', '')
  const heures = Number(chiffres.slice(0, 2))
  const minutes = chiffres.length > 2 ? Number(chiffres.slice(2, 4)) : 0
  return signe * (heures * 60 + minutes)
}

/** Une date ou un instant ISO, découpé : ses champs écrits et son décalage s'il en porte un. */
export function decouper(texte: string): { mur: Mur; decalage: number | null; avecHeure: boolean } | null {
  const m = MOTIF.exec(texte.trim())
  if (!m) return null
  const [, a, mo, j, h, mi, s, fraction, dec] = m
  const mur: Mur = {
    annee: Number(a),
    mois: Number(mo),
    jour: Number(j),
    heure: Number(h ?? 0),
    minute: Number(mi ?? 0),
    seconde: Number(s ?? 0) + (fraction ? Number(`0.${fraction}`) : 0),
  }
  const valide = new Date(Date.UTC(mur.annee, mur.mois - 1, mur.jour))
  if (valide.getUTCMonth() !== mur.mois - 1 || mur.heure > 23 || mur.minute > 59) return null
  return { mur, decalage: dec ? minutesDuDecalage(dec) : null, avecHeure: h != null }
}

/** Les champs d'une heure murale, comptés en millisecondes « comme si c'était du temps universel ». */
function versMs(mur: Mur): number {
  return Date.UTC(mur.annee, mur.mois - 1, mur.jour, mur.heure, mur.minute, 0) + mur.seconde * 1000
}

function depuisMs(ms: number): Mur {
  const d = new Date(ms)
  return {
    annee: d.getUTCFullYear(),
    mois: d.getUTCMonth() + 1,
    jour: d.getUTCDate(),
    heure: d.getUTCHours(),
    minute: d.getUTCMinutes(),
    seconde: d.getUTCSeconds(),
  }
}

/**
 * Recale l'écran sur l'heure du serveur. `recuLe` : l'instant du poste où la réponse est arrivée
 * (pour les essais). Rend `false` et ne change rien si l'en-tête manque ou ne se lit pas.
 */
export function recalerHorloge(entete: string | null | undefined, recuLe: number = Date.now()): boolean {
  if (!entete) return false
  const lu = decouper(entete)
  if (!lu || !lu.avecHeure) return false
  const murMs = versMs(lu.mur)
  decalageMur = murMs - recuLe
  if (lu.decalage != null) {
    decalageUsine = lu.decalage
    decalageInstant = murMs - lu.decalage * MINUTE - recuLe
  }
  return true
}

/** Oublie le recalage (essais, déconnexion) : l'écran revient à l'horloge du poste. */
export function reinitialiserHorloge(): void {
  decalageMur = decalageDuPoste()
  decalageInstant = null
  decalageUsine = null
}

/** L'heure murale de l'usine, maintenant. */
export function murUsine(): Mur {
  return depuisMs(Date.now() + decalageMur)
}

/** L'instant présent selon le serveur (millisecondes depuis 1970), pour compter des durées. */
export function instantServeur(): number {
  return Date.now() + (decalageInstant ?? 0)
}

/** Le décalage de l'usine sur le temps universel, en minutes (+60 pour +01:00), s'il est connu. */
export function decalageDeLUsine(): number | null {
  return decalageUsine
}

const deux = (n: number) => String(n).padStart(2, '0')

/** « AAAA-MM-JJ » d'une heure murale. */
export function jourIso(mur: Mur): string {
  return `${String(mur.annee).padStart(4, '0')}-${deux(mur.mois)}-${deux(mur.jour)}`
}

/** La date du jour à l'usine, « AAAA-MM-JJ » (borne `max` des champs de date). */
export function aujourdhui(): string {
  return jourIso(murUsine())
}

/** Le mois en cours à l'usine, « AAAA-MM ». */
export function moisCourant(): string {
  return aujourdhui().slice(0, 7)
}

/** « AAAA-MM-JJ » décalé de `jours` (négatif : dans le passé). */
export function ajouterJours(jour: string, jours: number): string {
  const lu = decouper(jour)
  if (!lu) return jour
  return jourIso(depuisMs(versMs({ ...lu.mur, heure: 12, minute: 0, seconde: 0 }) + Math.round(jours) * JOUR))
}

/** La date du jour à l'usine, décalée de `jours` (négatif : dans le passé). */
export function jourDansN(jours = 0): string {
  return ajouterJours(aujourdhui(), jours)
}

/** Le nombre de jours de `jour` à aujourd'hui (1 = hier, 0 = aujourd'hui, −1 = demain). */
export function joursDepuis(jour: string): number | null {
  const lu = decouper(jour)
  if (!lu) return null
  const debut = (m: Mur) => Date.UTC(m.annee, m.mois - 1, m.jour)
  return Math.round((debut(murUsine()) - debut(lu.mur)) / JOUR)
}

/** L'heure qu'il est à l'usine, « 13:20:46 ». */
export function heureServeur(): string {
  const m = murUsine()
  return `${deux(m.heure)}:${deux(m.minute)}:${deux(Math.floor(m.seconde))}`
}

/**
 * L'heure murale de l'usine d'une date ou d'un instant venu du serveur.
 *
 * Une date seule (« 2026-10-08 ») est un jour du calendrier de l'usine, jamais minuit UTC. Un
 * instant est présenté par le serveur à l'heure de l'usine : ses chiffres se lisent tels quels ;
 * s'il porte un autre décalage que celui de l'usine (« …Z »), il est ramené à l'heure de l'usine
 * dès que celle-ci est connue.
 */
export function murDe(valeur: string): { mur: Mur; avecHeure: boolean } | null {
  const lu = decouper(valeur)
  if (!lu) return null
  if (lu.decalage == null || decalageUsine == null || lu.decalage === decalageUsine) {
    return { mur: lu.mur, avecHeure: lu.avecHeure }
  }
  const instant = versMs(lu.mur) - lu.decalage * MINUTE
  return { mur: depuisMs(instant + decalageUsine * MINUTE), avecHeure: lu.avecHeure }
}

/** L'instant (ms depuis 1970) d'un horodatage du serveur ; sans décalage écrit, celui de l'usine. */
export function instantDe(valeur: string): number | null {
  const lu = decouper(valeur)
  if (!lu) return null
  const decalage = lu.decalage ?? decalageUsine
  // Décalage inconnu : l'heure murale se compare à l'heure murale tenue ici, sur l'horloge du
  // poste (`instantServeur()` vaut alors `Date.now()`), et la durée reste juste.
  if (decalage == null) return versMs(lu.mur) - decalageMur
  return versMs(lu.mur) - decalage * MINUTE
}
