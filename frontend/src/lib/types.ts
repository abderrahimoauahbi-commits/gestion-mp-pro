/**
 * Types de l'écran écrits à la main, et accès commode aux types générés depuis l'OpenAPI
 * (`types.gen.ts`, produit par `scripts/generer_types.sh`, jamais édité).
 *
 * Règle : un type qui décrit une réponse du serveur se lit dans `types.gen.ts` (`Schema<'MatiereFiche'>`),
 * jamais recopié à la main (Gestion MP recopiait ses types : ils divergeaient du serveur).
 */
import type { components } from './types.gen'

/** Les schémas de l'API par leur nom (`Schema<'CommandeFiche'>`), dès que le serveur les publie. */
type Schemas =
  components['schemas'] extends Record<string, unknown> ? components['schemas'] : Record<string, never>
export type Schema<N extends keyof Schemas> = Schemas[N]

/** Les rôles (MODELE-DONNEES § 2, `Role`) : direction, achats, alimentation, administrateur technique. */
export type Role = 'direction' | 'achats' | 'alimentation' | 'administrateur'

/** Le corps d'un refus du serveur (API-PRO § 0.3). */
export interface CorpsRefus {
  detail: string
  code: string
  /** Pour une saisie refusée (422) : chemin du champ → message. */
  champs?: Record<string, string>
}

/** Une page d'une longue liste (API-PRO § 0.1) : `?apres=suivant` lit la suivante. */
export interface Page<T> {
  elements: T[]
  total: number
  suivant: string | null
}
