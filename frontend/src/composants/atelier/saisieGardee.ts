/**
 * La saisie gardée de l'atelier (an. 17) : chaque écran de saisie (Envoyer, Retour, Déplacer,
 * Monter, Signaler) garde ce qu'on a tapé dans `sessionStorage`, et le reprend si l'on revient
 * (barre du bas, « ‹ », téléphone qui recharge la page). `oublier` l'efface une fois le geste
 * enregistré ou abandonné. Un stockage indisponible (navigation privée) ne casse rien.
 */
import { useCallback, useState } from 'react'

const PREFIXE = 'gestion-mp-pro:saisie:'

function lire<T>(cle: string, initial: T): T {
  try {
    const brut = sessionStorage.getItem(PREFIXE + cle)
    if (brut == null) return initial
    const lu: unknown = JSON.parse(brut)
    // Une saisie d'une autre forme (version précédente de l'écran) est ignorée.
    const memeForme = (v: unknown): v is T => typeof v === typeof initial && v !== null
    return memeForme(lu) ? lu : initial
  } catch {
    return initial
  }
}

function ecrire(cle: string, valeur: unknown): void {
  try {
    sessionStorage.setItem(PREFIXE + cle, JSON.stringify(valeur))
  } catch {
    /* stockage plein ou interdit : la saisie vit seulement en mémoire */
  }
}

/** Vrai si une saisie est gardée pour cet écran (pour dire « Saisie reprise »). */
export function saisieGardee(cle: string): boolean {
  try {
    return sessionStorage.getItem(PREFIXE + cle) != null
  } catch {
    return false
  }
}

export function useSaisieGardee<T>(
  cle: string,
  initial: T,
): [T, (suite: T | ((avant: T) => T)) => void, () => void] {
  const [valeur, setValeur] = useState<T>(() => lire(cle, initial))
  const poser = useCallback(
    (suite: T | ((avant: T) => T)) =>
      setValeur((avant) => {
        const estFonction = (x: unknown): x is (a: T) => T => typeof x === 'function'
        const v = estFonction(suite) ? suite(avant) : suite
        ecrire(cle, v)
        return v
      }),
    [cle],
  )
  const oublier = useCallback(() => {
    try {
      sessionStorage.removeItem(PREFIXE + cle)
    } catch {
      /* rien à oublier */
    }
  }, [cle])
  return [valeur, poser, oublier]
}
