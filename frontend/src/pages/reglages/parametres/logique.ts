/**
 * La logique des Paramètres, sans écran : ce que le serveur refuserait, dit **à la frappe** et
 * avec **la même phrase** (bornes, ordres des seuils, longueur des textes, adresses ; route 24,
 * `services/reglages.py` et `services/registre_reglages.py` du lot D1 — `logique.test.ts` relit
 * ces phrases dans les sources du serveur). Un taux est rangé en fraction et saisi en pourcent
 * (`echelle`). L'écriture est tout ou rien, à la `version_globale` lue.
 */
import { lireNombre } from '../../../composants/saisie/Nombre'
import { nombre } from '../../../lib/format'
import type { Schema } from '../../../lib/types'

export type Reglage = Schema<'Reglage'>

/** Une saisie en cours : un nombre dans l'unité affichée (% pour un taux), ou un texte. */
export type Brouillon = Readonly<Record<string, string>>

export const TEXTE_MAX = 500
export const ADRESSE_MAX = 200
export const ADRESSE_COURRIEL = /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/

/** (plus petit, plus grand, refus) : l'égalité est refusée. */
export const ORDRES_STRICTS: readonly (readonly [string, string, string])[] = [
  [
    'seuil_critique',
    'seuil_alerte',
    'La couverture critique doit rester inférieure à la couverture d’ATTENTION : sinon plus aucune matière ne serait en ATTENTION.',
  ],
  ['seuil_abc_a', 'seuil_abc_b', 'La part cumulée de la classe A doit rester sous celle de la classe B.'],
  [
    'seuil_tier3',
    'seuil_tier2',
    'Le montant du Tier 3 doit rester sous celui du Tier 2 : sinon plus aucune ligne ne serait en Tier 3.',
  ],
  ['seuil_xyz_x', 'seuil_xyz_y', 'Le CV maximum de la classe X doit rester sous celui de la classe Y.'],
  ['score_surveiller', 'score_standard', 'Le score « ATTENTION » doit rester sous le score « standard ».'],
  ['score_standard', 'score_strategique', 'Le score « standard » doit rester sous le score « stratégique ».'],
]

/** (plus petit, plus grand, refus) : l'égalité est permise. */
export const ORDRES_LARGES: readonly (readonly [string, string, string])[] = [
  [
    'seuil_tier2',
    'seuil_tier1',
    'Le montant du Tier 1 (classe A) ne peut pas être inférieur à celui du Tier 2.',
  ],
]

/** Les familles montrées ailleurs que dans « Paramètres » (période close, réglages techniques). */
export const FAMILLES_AILLEURS = new Set(['Période close', 'Technique'])

/** La valeur rangée d'un réglage numérique, dans l'unité affichée (2 % pour 0,02). */
export function enAffichage(r: Reglage, valeur: string): number | null {
  const lu = Number(valeur)
  if (valeur.trim() === '' || !Number.isFinite(lu))
    return typeof r.defaut === 'number' ? r.defaut * r.echelle : null
  return Number((lu * (r.echelle || 1)).toPrecision(12))
}

/** La saisie d'un nombre (unité affichée) en valeur rangée (fraction pour un taux). */
export function enRangee(r: Reglage, saisie: number): number {
  return Number((saisie / (r.echelle || 1)).toPrecision(12))
}

/** Une borne écrite comme le serveur l'écrit (« 0,5 », « 1 000 000 000 000 »). */
const borne = (x: number) => nombre(x, 0, 6)

/** Le texte initial d'un champ : la valeur en base, dans l'unité affichée. */
export function texteInitial(r: Reglage): string {
  if (r.texte) return r.valeur
  const v = enAffichage(r, r.valeur)
  return v == null ? '' : String(v).replace('.', ',')
}

/** Le refus d'un champ seul (`''` s'il passe) : nombre, bornes, longueur, adresses. */
export function refusDuChamp(r: Reglage, saisie: string): string {
  if (r.texte) return refusDuTexte(r, saisie)
  const v = lireNombre(saisie)
  if (v == null) return `« ${r.libelle} » attend un nombre.`
  const echelle = r.echelle || 1
  const bas = r.bas == null ? -Infinity : r.bas * echelle
  const haut = r.haut == null ? Infinity : r.haut * echelle
  if (v < bas - 1e-9 || v > haut + 1e-9) {
    return `« ${r.libelle} » doit rester entre ${borne(bas)} et ${borne(haut)} ${r.unite} — reçu ${borne(v)}.`
  }
  return ''
}

function refusDuTexte(r: Reglage, saisie: string): string {
  const valeur = saisie.trim()
  if (r.cle === 'adresse_publique') {
    if (valeur && !(/^https?:\/\//.test(valeur) && valeur.length <= ADRESSE_MAX && !valeur.includes(' '))) {
      return 'L’adresse commence par http:// ou https:// (ex. http://mac-usine:8050).'
    }
    return ''
  }
  if (valeur.length > TEXTE_MAX) return `« ${r.libelle} » : texte trop long.`
  if (r.cle === 'courriel_destinataires' && valeur) {
    const fausses = adressesIllisibles(valeur)
    if (fausses.length) {
      return `Adresse de courriel illisible : ${fausses.join(', ')} (ex. direction@usine.ma, séparées par des virgules).`
    }
  }
  return ''
}

/** Les adresses de courriel qu'on ne sait pas lire, d'une liste séparée par « , » ou « ; ». */
export function adressesIllisibles(texte: string): string[] {
  return texte
    .split(/[,;]/)
    .map((x) => x.trim())
    .filter((x) => x && !ADRESSE_COURRIEL.test(x))
}

/** La valeur finale (affichée) d'un réglage numérique : la saisie, sinon la base. */
function valeurFinale(
  reglages: ReadonlyMap<string, Reglage>,
  brouillon: Brouillon,
  cle: string,
): number | null {
  const r = reglages.get(cle)
  if (!r) return null
  return cle in brouillon ? (lireNombre(brouillon[cle] ?? '') ?? null) : enAffichage(r, r.valeur)
}

/** Les ordres que l'état final ne tient pas (même phrase que le serveur). */
export function desordres(reglages: readonly Reglage[], brouillon: Brouillon): string[] {
  const parCle = new Map(reglages.map((r) => [r.cle, r]))
  const v = (cle: string) => valeurFinale(parCle, brouillon, cle)
  const sauf = (a: number | null, b: number | null) => a == null || b == null
  return [
    ...ORDRES_STRICTS.filter(([a, b]) => !sauf(v(a), v(b)) && (v(a) ?? 0) >= (v(b) ?? 0)),
    ...ORDRES_LARGES.filter(([a, b]) => !sauf(v(a), v(b)) && (v(a) ?? 0) > (v(b) ?? 0)),
  ].map(([, , m]) => m)
}

/** Tous les refus de la saisie : champ par champ, puis les ordres. */
export function refus(reglages: readonly Reglage[], brouillon: Brouillon): string[] {
  const parChamp = reglages
    .filter((r) => r.cle in brouillon)
    .map((r) => refusDuChamp(r, brouillon[r.cle] ?? ''))
  return [...parChamp.filter(Boolean), ...desordres(reglages, brouillon)]
}

/** Pose une saisie : retirée du brouillon si elle revient à la valeur en base. */
export function poser(brouillon: Brouillon, r: Reglage, saisie: string): Brouillon {
  const suite = { ...brouillon }
  const initial = texteInitial(r)
  const pareil = r.texte ? saisie === initial : lireNombre(saisie) === lireNombre(initial)
  if (pareil) delete suite[r.cle]
  else suite[r.cle] = saisie
  return suite
}

/** Le corps du `PUT parametres` : chaque saisie en valeur rangée, et la version globale lue. */
export function corps(reglages: readonly Reglage[], brouillon: Brouillon) {
  const valeurs: Record<string, string | number> = {}
  for (const r of reglages) {
    const saisie = brouillon[r.cle]
    if (saisie === undefined) continue
    valeurs[r.cle] = r.texte ? saisie.trim() : enRangee(r, lireNombre(saisie) ?? 0)
  }
  return { valeurs, version_globale: reglages[0]?.version_globale ?? 0 }
}

/** Une valeur rangée, lisible (« 2 % », « 60 jours », « — »). */
export function lisible(r: Reglage, valeur: string | number): string {
  if (r.texte) return String(valeur) || '—'
  const v = enAffichage(r, String(valeur))
  return v == null ? '—' : `${nombre(v, 0, 3)}${r.unite ? ` ${r.unite}` : ''}`
}
