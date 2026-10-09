/**
 * L'écart d'une sortie au prévu de la recette, **une seule règle** (P2-8, P2-25 ; ECRANS-PRO
 * `EcartFil`) : « conforme » sous 0,05 kg ou 0,5 % ; à 5 % près c'est juste (ok) ; au-delà, un
 * excès est à surveiller (attention), un manque est critique. Sorties, fiche d'ordre, traçabilité,
 * saisie d'ordre au bureau et au téléphone la lisent. Partie du moteur `lib/ordre.ts`.
 */
import type { Ton } from './statuts'
import { contenance } from './unites'
import type { Fil, Prise } from './ordre'

/** Le seuil au-delà duquel un écart se signale (5 %). */
export const SEUIL_ECART = 0.05

/** Le ton d'un écart relatif : ok à 5 % près, attention en plus, critique en moins. */
export function tonEcart(relatif: number | null | undefined): Ton | undefined {
  if (relatif == null) return undefined
  if (Math.abs(relatif) <= SEUIL_ECART) return 'ok'
  return relatif > 0 ? 'attention' : 'critique'
}

/** L'écart relatif (sorti − prévu) ÷ prévu, ou `null` sans prévu. */
export function ecartRelatif(sorti: number, prevu: number): number | null {
  return prevu ? (sorti - prevu) / prevu : null
}

export interface EcartLisible {
  /** Sous 0,05 kg ou 0,5 % : « conforme ». */
  conforme: boolean
  ton: Ton
  relatif: number
}

/** L'écart d'un fil au prévu (en kilos), lisible ; `null` sans prévu. */
export function ecartLisible(ecart: number | null, prevu: number): EcartLisible | null {
  if (ecart == null || !prevu) return null
  const relatif = ecart / prevu
  if (Math.abs(ecart) < 0.05 || Math.abs(relatif) < 0.005) return { conforme: true, ton: 'ok', relatif }
  return { conforme: false, ton: tonEcart(relatif) ?? 'neutre', relatif }
}

/** Vrai si la prise demande plus que ce que porte le lot (`dispo` < 0 : pas encore connu). */
export function depasse(p: Prise, dispo: number): boolean {
  return dispo >= 0 && (p.kg ?? 0) > dispo + 0.0005
}

/** Un fil « tout est conforme » : écart conforme, sans manque, ni dépassement, ni contenance manquante. */
export function filConforme(f: Fil, dispo: (p: Prise) => number): boolean {
  if (!f.besoin || f.besoin.manque > 0.05) return false
  if (!ecartLisible(f.ecart, f.besoin.prevu)?.conforme) return false
  return f.prises.every(
    (p) =>
      !depasse(p, dispo(p)) &&
      contenance(
        { poidsBobine: p.poids_bobine, bobinesPalette: p.bobines_palette, kgParMl: p.kg_par_ml },
        p.unite,
      ) != null,
  )
}
