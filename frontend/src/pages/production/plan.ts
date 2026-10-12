/**
 * Le plan de production à la frappe (`VoletPlan` de Gestion MP) : une qualité se planifie par une
 * base mensuelle (un mois ordinaire) et douze coefficients de saisonnalité ; taper les m² d'un mois
 * en donne le coefficient (m² ÷ base), taper un coefficient en donne les m² : **la base ne change
 * jamais d'elle-même**, seulement quand on la saisit (décision de Mohamed, 12/10/2026). Le serveur refuse un
 * coefficient hors de 0 à 20 : l'écran ne laisse pas cliquer (P2-12).
 */
import { arrondi } from '../../lib/format'
import type { Schema } from '../../lib/types'

export type PlanProduction = Schema<'PlanProduction'>
export type QualitePlan = Schema<'QualitePlan'>
export type PlanEtRealise = Schema<'PlanEtRealise'>
export type RealiseQualite = Schema<'RealiseQualite'>
export type BesoinsDetailles = Schema<'BesoinsDetailles'>
export type BesoinMatiere = Schema<'BesoinMatiere'>

/** Ce que la direction a tapé et pas encore enregistré, pour une qualité. */
export interface SaisiePlan {
  base_mensuelle: number
  saisonnalite: number[]
}
export type BrouillonPlan = Readonly<Record<number, SaisiePlan>>

export const MOIS_CALENDAIRES = [
  'Janv.',
  'Févr.',
  'Mars',
  'Avr.',
  'Mai',
  'Juin',
  'Juil.',
  'Août',
  'Sept.',
  'Oct.',
  'Nov.',
  'Déc.',
]

/** Les bornes d'un coefficient de saisonnalité (refus du serveur au-delà). */
export const COEF_MIN = 0
export const COEF_MAX = 20

export const somme = (v: readonly number[]) => v.reduce((s, x) => s + x, 0)

export function saisieDe(q: Pick<QualitePlan, 'base_mensuelle' | 'saisonnalite'>): SaisiePlan {
  return {
    base_mensuelle: q.base_mensuelle,
    saisonnalite: q.saisonnalite.length === 12 ? [...q.saisonnalite] : Array<number>(12).fill(1),
  }
}

export function egales(a: SaisiePlan, b: SaisiePlan): boolean {
  return (
    Math.abs(a.base_mensuelle - b.base_mensuelle) < 1e-9 &&
    a.saisonnalite.every((c, i) => Math.abs(c - (b.saisonnalite[i] ?? 0)) < 1e-9)
  )
}

export const horsBornes = (s: SaisiePlan) => s.saisonnalite.some((c) => c < COEF_MIN || c > COEF_MAX)

/**
 * Les m² d'un mois changent : seul le coefficient de ce mois suit (m² ÷ base, 6 décimales) ; la
 * base et les autres mois ne bougent pas. Sans base, les m² ne donnent pas de coefficient : rien
 * ne change (l'écran grise alors la cellule, `SANS_BASE`).
 */
export function depuisM2(s: SaisiePlan, mois: number, m2: number): SaisiePlan {
  if (s.base_mensuelle <= 0) return s
  const coef = arrondi(m2 / s.base_mensuelle, 6)
  return { ...s, saisonnalite: s.saisonnalite.map((c, i) => (i === mois ? coef : c)) }
}

/** Pourquoi un mois ne se saisit pas en m² : sans base, pas de coefficient. */
export const SANS_BASE =
  'Saisir d’abord la base / mois : les m² d’un mois donnent son coefficient (m² ÷ base).'

/** Le brouillon après une saisie : une ligne revenue à son état enregistré n'est plus modifiée. */
export function modifier(b: BrouillonPlan, q: QualitePlan, s: SaisiePlan): BrouillonPlan {
  const suite = { ...b }
  if (egales(s, saisieDe(q))) delete suite[q.id]
  else suite[q.id] = s
  return suite
}

export function oublier(b: BrouillonPlan, ids: readonly number[]): BrouillonPlan {
  const suite = { ...b }
  for (const id of ids) delete suite[id]
  return suite
}

/** L'état d'une qualité au plan (famille `qualite_plan` des badges). */
export function etatAuPlan(q: QualitePlan, s: SaisiePlan): string {
  if (!q.actif) return 'inactive'
  if (s.base_mensuelle > 0 && q.lignes_recette === 0) return 'sans_recette'
  if (!q.recette_conforme) return 'recette_incomplete'
  return s.base_mensuelle > 0 ? 'au_plan' : 'pas_de_plan'
}

/** Le rang du premier mois compté dans l'écart (mois de mise en service), ou 0. */
export function debutCompte(r: Pick<PlanEtRealise, 'mois' | 'debut_service'>): number {
  if (!r.debut_service) return 0
  const i = r.mois.findIndex((m) => m >= (r.debut_service ?? ''))
  return i < 0 ? r.mois.length : i
}

/**
 * Le rang du premier mois à afficher (affichage seulement, l'écart garde `debutCompte`).
 *
 * Tant qu'un mois est AVANT le mois en cours (le dernier de la série) et que toutes les
 * qualités y ont plan = 0 et réalisé = 0, on le masque. On s'arrête au premier mois qui
 * porte une donnée, ou au mois en cours : celui-ci et les suivants ne sont jamais masqués.
 * Sur la base neuve l'historique vide d'avant le démarrage disparaît ; avec un historique,
 * le premier mois non vide ramène toute la série.
 */
export function debutAffiche(r: Pick<PlanEtRealise, 'mois' | 'lignes'>): number {
  const dernier = r.mois.length - 1
  let i = 0
  while (i < dernier && r.lignes.every((x) => !(x.plan[i] ?? 0) && !(x.realise[i] ?? 0))) {
    i++
  }
  return Math.max(0, i)
}

/** L'écart des mois clos, toutes qualités : (tissé − prévu) ÷ prévu, ou `null`. */
export function ecartClos(r: PlanEtRealise): {
  ecart: number | null
  prevu: number
  fait: number
  mois: number
} {
  const debut = debutCompte(r)
  const clos = r.mois_clos
  const prevu = somme(r.lignes.map((x) => somme(x.plan.slice(debut, clos))))
  const fait = somme(r.lignes.map((x) => somme(x.realise.slice(debut, clos))))
  return { ecart: prevu ? (fait - prevu) / prevu : null, prevu, fait, mois: Math.max(0, clos - debut) }
}

/** Le ton d'un écart au plan : à 10 % près c'est juste, un retard est critique, une avance à surveiller. */
export function tonEcartPlan(e: number | null | undefined) {
  if (e == null) return undefined
  if (Math.abs(e) <= 0.1) return 'ok' as const
  return e > 0 ? ('attention' as const) : ('critique' as const)
}
