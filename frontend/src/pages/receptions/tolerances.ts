/**
 * Les tolérances de la réception (écart de pesée, poids de bobine, excédent), lues dans les
 * réglages (`GET /parametres`, lecture permise aux achats) : jamais écrites en dur à l'écran.
 */
import { useLecture } from '../../lib/requetes'
import { TOLERANCES_DEFAUT, type Tolerances } from './calculSaisie'
import type { Reglage } from './types'

function valeur(reglages: readonly Reglage[] | undefined, cle: string, defaut: number): number {
  const r = reglages?.find((x) => x.cle === cle)
  const v = Number(r?.valeur)
  return r && r.valeur !== '' && Number.isFinite(v) ? v : defaut
}

export function lireTolerances(reglages: readonly Reglage[] | undefined): Tolerances {
  return {
    pesee: valeur(reglages, 'toler_ecart_pesee', TOLERANCES_DEFAUT.pesee),
    bobine: valeur(reglages, 'toler_poids_bobine', TOLERANCES_DEFAUT.bobine),
    excedent: valeur(reglages, 'toler_excedent', TOLERANCES_DEFAUT.excedent),
  }
}

export function useTolerances(): Tolerances {
  const lu = useLecture<Reglage[]>('/parametres')
  return lireTolerances(lu.data)
}
