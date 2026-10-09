/**
 * Les liens vers les écrans des autres domaines ne sont des liens que si le rôle peut les ouvrir
 * (docs/lots/E2.md : `permis(role, adresse)` avant de rendre un lien) ; sinon le texte reste.
 */
import { permis } from '../../lib/droits'
import type { Role } from '../../lib/types'

/** L'adresse si ce rôle peut l'ouvrir, sinon `null`. */
export function lienSi(role: Role, adresse: string): string | null {
  return permis(role, adresse) ? adresse : null
}

/** La fiche de stock d'une matière (ECRANS-PRO 4.3 : `/stock/matieres/:id`). */
export const adresseMatiere = (id: number) => `/stock/matieres/${id}`
