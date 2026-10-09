/**
 * Comparer une version de la recette à celle en vigueur (onglet « Versions ») : les parts, ligne
 * par ligne (ajoutée depuis, retirée depuis, écart en points), et les poids au m².
 */
import type { VersionRecette } from './types'

export interface Ecart {
  cle: string
  role: string
  reference: string
  ici: number | null
  enVigueur: number | null
}

/** Les lignes qui diffèrent entre la version choisie et celle en vigueur. */
export function ecarts(choisie: VersionRecette, vigueur: VersionRecette): Ecart[] {
  const cle = (l: { matiere_id: number }) => String(l.matiere_id)
  const ici = new Map(choisie.lignes.map((l) => [cle(l), l]))
  const la = new Map(vigueur.lignes.map((l) => [cle(l), l]))
  const toutes = [...new Set([...ici.keys(), ...la.keys()])]
  return toutes
    .map((k) => {
      const a = ici.get(k)
      const b = la.get(k)
      return {
        cle: k,
        role: (a ?? b)?.role ?? '',
        reference: (a ?? b)?.reference ?? '',
        ici: a?.pourcentage ?? null,
        enVigueur: b?.pourcentage ?? null,
      }
    })
    .filter((e) => e.ici == null || e.enVigueur == null || Math.abs(e.ici - e.enVigueur) > 1e-9)
    .sort((x, y) => x.role.localeCompare(y.role) || x.reference.localeCompare(y.reference))
}

/** « ajoutée depuis », « retirée depuis », « +2,00 pt ». */
export function ecartLisible(e: Ecart, nombre: (v: number, d: number) => string): string {
  if (e.ici == null) return 'ajoutée depuis'
  if (e.enVigueur == null) return 'retirée depuis'
  const d = e.enVigueur - e.ici
  return `${d > 0 ? '+' : '−'}${nombre(Math.abs(d), 2)} pt`
}

/** Les poids qui diffèrent : « Poil 0,800 (en vigueur : 0,750) ». */
export function ecartsPoids(
  choisie: VersionRecette,
  vigueur: VersionRecette,
): { role: string; ici: number; enVigueur: number }[] {
  if (!choisie.poids) return []
  const la = new Map((vigueur.poids ?? []).map((p) => [p.role_id, p.poids]))
  const ici = new Map(choisie.poids.map((p) => [p.role_id, p]))
  const roles = new Set([...ici.keys(), ...la.keys()])
  return [...roles]
    .map((r) => ({
      role: ici.get(r)?.role ?? vigueur.poids?.find((p) => p.role_id === r)?.role ?? '',
      ici: ici.get(r)?.poids ?? 0,
      enVigueur: la.get(r) ?? 0,
    }))
    .filter((p) => Math.abs(p.ici - p.enVigueur) > 1e-9)
}
