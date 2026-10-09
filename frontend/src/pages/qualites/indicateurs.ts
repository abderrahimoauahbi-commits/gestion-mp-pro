/**
 * Les indicateurs de la page des qualités, sur **la même base que la nomenclature** : les
 * qualités en service (les arrêtées sont signalées à part, P7-27). Formules dans `aide.json`.
 */
import type { Qualite } from './types'

/** Les rôles d'une qualité qui pèsent sans aucune matière dans sa recette. */
export function rolesSansMatiere(q: Qualite): string[] {
  const portes = new Set(q.recette.map((l) => l.role_id))
  return q.poids.filter((p) => p.poids > 0 && !portes.has(p.role_id)).map((p) => p.role)
}

/** Une recette est juste si chaque rôle fait 100 % et qu'aucun rôle pesant ne manque de matière. */
export function recetteJuste(q: Qualite): boolean {
  return q.controle.conforme && rolesSansMatiere(q).length === 0
}

export interface Synthese {
  fabriquees: number
  arretees: number
  incompletes: string[]
  incompletesArretees: number
  planMensuel: number
  /** Σ(coût × base) / Σ base des qualités en service ; `null` sans coût (alimentation) ou sans plan. */
  coutMoyen: number | null
}

export function synthese(qualites: readonly Qualite[]): Synthese {
  const actives = qualites.filter((q) => q.actif)
  const base = actives.reduce((s, q) => s + q.base_mensuelle, 0)
  const avecCout = actives.every((q) => q.cout_m2_mad != null)
  const pondere = actives.reduce((s, q) => s + (q.cout_m2_mad ?? 0) * q.base_mensuelle, 0)
  return {
    fabriquees: actives.length,
    arretees: qualites.length - actives.length,
    incompletes: actives.filter((q) => !recetteJuste(q)).map((q) => q.code),
    incompletesArretees: qualites.filter((q) => !q.actif && !recetteJuste(q)).length,
    planMensuel: base,
    coutMoyen: avecCout && base > 0 ? pondere / base : null,
  }
}
