/**
 * Ce que le serveur refusera à la validation d'un ordre, dit d'avance **avec ses mots**
 * (`services/ordres/proposition.empechements`, `ordres/blocages.lots_manquants`,
 * `periode.date_permise`) ; « commentaire » y devient « observations » (vocabulaire, an. 8). Une
 * seule fois pour le bureau et le téléphone. Partie du moteur `lib/ordre.ts`.
 */
import { date as dateLisible, kg } from './format'
import type { Prise } from './ordre'
import type { Schema } from './types'

export interface ContexteBlocages {
  jour: string
  aujourdhui: string
  /** Dernier jour de la période close, s'il y en a une. */
  cloture: string | null
  /** La date du dernier ordre validé ou annulé (les numéros suivent les dates). */
  dernier: string | null
  /** Le magasin de l'ordre : son code (les phrases du serveur), son nom (les inventaires du contexte). */
  magasin: { code: string; nom: string }
  inventaires: readonly {
    numero: string
    date: string
    magasin: string | null
    matieres: readonly number[]
  }[]
  /** Le disponible de chaque lot dans le magasin, à la date de l'ordre ; `null` tant qu'il se lit. */
  dispo: ReadonlyMap<number, number> | null
}

/** La date du dernier ordre validé ou annulé (un annulé garde son numéro), hors `sauf`. */
export function dernierOrdre(
  ordres: readonly Pick<Schema<'OrdreResume'>, 'id' | 'date' | 'statut'>[] | undefined,
  sauf?: number | null,
): string | null {
  let dernier: string | null = null
  for (const o of ordres ?? []) {
    if (o.statut === 'brouillon' || o.id === sauf) continue
    if (!dernier || o.date > dernier) dernier = o.date
  }
  return dernier
}

/** L'ordre daté avant le dernier ordre validé (les numéros suivent les dates, M67) ; '' sinon. */
export function blocageDate(jour: string, dernier: string | null): string {
  if (!dernier || !jour || jour >= dernier) return ''
  const d = dateLisible(dernier)
  return (
    `Un ordre du ${d} est déjà validé : les numéros suivent les dates, cet ordre ne peut pas être ` +
    `daté avant. Pour un oubli, le dater du ${d} et écrire la vraie date dans les observations.`
  )
}

/** Un inventaire ouvert qui suspend les mouvements de l'ordre. */
export function texteInventaire(i: ContexteBlocages['inventaires'][number]): string {
  return `L'inventaire ${i.numero} (${i.magasin ?? 'tous les magasins'}, du ${dateLisible(i.date)}) est en cours : les mouvements y sont suspendus jusqu'à sa validation. Garder en brouillon, ou attendre.`
}

/** Les inventaires ouverts qui comptent une matière de l'ordre dans son magasin (K2). */
function inventaires(prises: readonly Prise[], c: ContexteBlocages): string[] {
  const matieres = new Set(prises.filter((p) => (p.kg ?? 0) >= 0.001).map((p) => p.matiere_id))
  return c.inventaires
    .filter((i) => (!i.magasin || i.magasin === c.magasin.nom) && i.matieres.some((m) => matieres.has(m)))
    .map(texteInventaire)
}

/** Les lots qui ne portent pas, à la date, ce que l'ordre leur demande (lignes additionnées). */
function lotsManquants(prises: readonly Prise[], c: ContexteBlocages): string[] {
  if (!c.dispo) return []
  const voulu = new Map<number, { p: Prise; kg: number }>()
  for (const p of prises) {
    if ((p.kg ?? 0) < 0.001) continue
    const v = voulu.get(p.lot_id)
    voulu.set(p.lot_id, { p, kg: (v?.kg ?? 0) + (p.kg ?? 0) })
  }
  const raisons: string[] = []
  for (const { p, kg: demande } of voulu.values()) {
    const present = c.dispo.get(p.lot_id) ?? 0
    if (demande > present + 0.0005)
      raisons.push(
        `lot ${p.lot} de ${p.reference} : ${present > 0.0005 ? `${kg(present)} seulement` : 'épuisé'} dans « ${c.magasin.code} », ${kg(demande)} demandés`,
      )
  }
  return raisons
}

/** Tout ce que le serveur refusera à la validation, dans l'ordre de ses contrôles. */
export function blocagesSaisie(prises: readonly Prise[], c: ContexteBlocages): string[] {
  const raisons: string[] = []
  if (c.jour > c.aujourdhui)
    raisons.push(`Date dans le futur (${dateLisible(c.jour)}) : un mouvement se saisit le jour où il a lieu.`)
  if (c.cloture && c.jour && c.jour <= c.cloture)
    raisons.push(
      `La période jusqu'au ${dateLisible(c.cloture)} est close : rien ne s'y écrit plus. Dater après la clôture, ou demander à la direction de la rouvrir.`,
    )
  raisons.push(...inventaires(prises, c))
  const date = blocageDate(c.jour, c.dernier)
  if (date) raisons.push(date)
  raisons.push(...lotsManquants(prises, c))
  return raisons
}
