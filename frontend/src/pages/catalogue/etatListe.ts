/**
 * L'état d'une liste du catalogue ou des qualités dans l'adresse : sa recherche et ses filtres,
 * sous des noms **propres à l'onglet** (P7-18, P7-28 : chaque onglet garde ses filtres, changer
 * d'onglet ne les perd plus, et ceux d'un onglet ne filtrent pas l'autre). « Effacer les filtres »
 * remet **tout** au défaut d'un coup — filtres, recherche et état (Actives) — et nettoie l'adresse
 * (P7-31).
 *
 * `etat` : un filtre d'état à défaut non vide (« Actives ») ; posé, il compte pour un critère.
 */
import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

import { avecParametre } from '../../lib/adresse'
import type { Choix } from '../../composants/tableaux/filtrage'

export interface EtatListe {
  recherche: { valeur: string; onChange: (q: string) => void }
  choix: { valeurs: Choix; poser: (cle: string, valeur: string | null) => void; effacer: () => void }
  /** La valeur d'un paramètre de la liste ('' s'il n'est pas posé). */
  lire: (cle: string) => string
}

export function useEtatListe(cleRecherche: string, cles: readonly string[]): EtatListe {
  const [params, setParams] = useSearchParams()
  const signature = cles.join('|')
  const q = params.get(cleRecherche) ?? ''
  const valeurs = useMemo(() => {
    const v: Record<string, string> = {}
    for (const c of signature.split('|')) {
      const lu = c ? params.get(c) : null
      if (lu) v[c] = lu
    }
    return v
  }, [params, signature])
  const onChange = useCallback(
    (texte: string) => setParams((p) => avecParametre(p, cleRecherche, texte), { replace: true }),
    [setParams, cleRecherche],
  )
  const poser = useCallback(
    (cle: string, valeur: string | null) =>
      setParams((p) => avecParametre(p, cle, valeur), { replace: true }),
    [setParams],
  )
  const effacer = useCallback(
    () =>
      setParams(
        (p) => {
          const suite = new URLSearchParams(p)
          for (const c of [...signature.split('|'), cleRecherche]) if (c) suite.delete(c)
          return suite
        },
        { replace: true },
      ),
    [setParams, signature, cleRecherche],
  )
  const lire = useCallback((cle: string) => params.get(cle) ?? '', [params])
  return { recherche: { valeur: q, onChange }, choix: { valeurs, poser, effacer }, lire }
}

/** L'état d'une fiche (Actives par défaut, Toutes, Désactivées), lu dans un paramètre de l'adresse. */
export type EtatFiche = 'actives' | 'toutes' | 'desactivees'

export function lireEtat(valeur: string): EtatFiche {
  return valeur === 'toutes' || valeur === 'desactivees' ? valeur : 'actives'
}

/** Vrai si la fiche passe le filtre d'état. */
export function passeEtat(actif: boolean, etat: EtatFiche): boolean {
  return etat === 'toutes' || (etat === 'actives' ? actif : !actif)
}
