/**
 * Le calcul d'une recette à la frappe, **comme le serveur** (`calcul/nomenclature.py`, CALCULS
 * § 3.5 ; formules dans `aide.json`) :
 * - rôle au mètre (cuir, franges, ruban) : son poids se saisit en ml/m² ; ml/m² d'une matière =
 *   part / 100 × poids du rôle ; kg/m² = ml/m² × densité de la matière (kg/ml) ;
 * - rôle au poids : kg/m² = part / 100 × poids du rôle ;
 * - coût/m² (MAD) = kg/m² × prix au kilo × cours de la devise × (1 + perte) ;
 * - un rôle est juste si |Σ parts − 100| ≤ 0,01 point ; un rôle pesant sans matière manque.
 */
import type { FacteursCout } from './types'

/** La tolérance du contrôle des 100 % (= C01, serveur). */
export const TOLERANCE = 0.01

export interface RoleQualite {
  role_id: number
  role: string
  lineaire: boolean
}

export interface LigneSaisie {
  matiere_id: number
  reference: string
  nature: string
  designation: string
  fournisseur: string
  role_id: number | null
  pourcentage: number
  /** kg/ml ; 0 inconnue. */
  densite: number
  prix_kg: number | null
  prix: number | null
  unite_prix: string | null
  devise: string | null
  /** La matière n'est plus au catalogue : la ligne sera retirée à l'enregistrement. */
  disparue: boolean
}

export interface LigneCalculee extends LigneSaisie {
  ml_m2: number | null
  kg_m2: number
  cout_m2: number | null
}

/** Une ligne calculée, avec le poids de son rôle (ml/m² pour un rôle au mètre). */
export function calculer(
  l: LigneSaisie,
  poidsRole: number,
  lineaire: boolean,
  f: FacteursCout | null,
): LigneCalculee {
  const ml = lineaire ? (l.pourcentage / 100) * poidsRole : null
  const kg = ml != null ? ml * (l.densite || 0) : (l.pourcentage / 100) * poidsRole
  const cours = l.devise ? f?.cours?.[l.devise] : undefined
  const cout = f?.cours && l.prix_kg != null && cours != null ? kg * l.prix_kg * cours * f.perte : null
  return { ...l, ml_m2: ml, kg_m2: kg, cout_m2: cout }
}

export type EtatRole = 'complet' | 'vide' | 'trop' | 'manque'

/** L'état d'un rôle d'après la somme de ses parts. */
export function etatRole(somme: number, lignes: number): EtatRole {
  if (!lignes) return 'vide'
  if (Math.abs(somme - 100) <= TOLERANCE) return 'complet'
  return somme > 100 ? 'trop' : 'manque'
}

export interface GroupeRole extends RoleQualite {
  poids: number
  lignes: LigneCalculee[]
  somme: number
  etat: EtatRole
  kg_m2: number
  cout_m2: number | null
}

/** Les rôles de la recette (ceux qui pèsent et ceux qui ont des lignes), dans l'ordre donné. */
export function grouper(
  roles: readonly RoleQualite[],
  poids: ReadonlyMap<number, number>,
  lignes: readonly LigneSaisie[],
  f: FacteursCout | null,
): GroupeRole[] {
  return roles
    .filter((r) => (poids.get(r.role_id) ?? 0) > 0 || lignes.some((l) => l.role_id === r.role_id))
    .map((r) => {
      const p = poids.get(r.role_id) ?? 0
      const calc = lignes.filter((l) => l.role_id === r.role_id).map((l) => calculer(l, p, r.lineaire, f))
      const somme = calc.reduce((s, l) => s + l.pourcentage, 0)
      const couts = calc.map((l) => l.cout_m2)
      return {
        ...r,
        poids: p,
        lignes: calc,
        somme,
        etat: etatRole(somme, calc.length),
        kg_m2: calc.reduce((s, l) => s + l.kg_m2, 0),
        cout_m2: couts.every((c) => c != null) ? couts.reduce<number>((s, c) => s + (c ?? 0), 0) : null,
      }
    })
}

export interface Bilan {
  /** Rôles dont les parts ne font pas 100 % (lignes présentes). */
  faux: string[]
  /** Rôles qui pèsent sans aucune matière. */
  sansMatiere: string[]
  kg_m2: number
  cout_m2: number | null
  matieres: number
  roles: number
}

export function bilan(groupes: readonly GroupeRole[]): Bilan {
  const couts = groupes.map((g) => g.cout_m2)
  return {
    faux: groupes.filter((g) => g.etat === 'trop' || g.etat === 'manque').map((g) => g.role),
    sansMatiere: groupes.filter((g) => g.etat === 'vide' && g.poids > 0).map((g) => g.role),
    kg_m2: groupes.reduce((s, g) => s + g.kg_m2, 0),
    cout_m2: couts.every((c) => c != null) ? couts.reduce<number>((s, c) => s + (c ?? 0), 0) : null,
    matieres: groupes.reduce((s, g) => s + g.lignes.length, 0),
    roles: groupes.length,
  }
}

/**
 * Ce qui empêche d'enregistrer (D-05, même règle que le serveur) : un rôle faux, toujours ; un
 * rôle pesant sans matière, pour une qualité en service dont la recette change ou est déjà
 * commencée (une arrêtée, ou une recette vide qu'on ne touche pas, est acceptée avec un
 * avertissement du serveur).
 */
export function aCorriger(b: Bilan, actif: boolean, recetteChangee: boolean): string[] {
  const bloquant = actif && (recetteChangee || b.matieres > 0)
  return [...b.faux, ...(bloquant ? b.sansMatiere : [])]
}

/** Ce qui reste à un rôle pour faire 100 % (la part d'une matière ajoutée). */
export function reste(somme: number): number {
  return Math.max(0, Math.round((100 - somme) * 100) / 100)
}
