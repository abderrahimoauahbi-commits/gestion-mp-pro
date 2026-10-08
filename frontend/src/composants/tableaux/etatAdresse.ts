/**
 * L'état d'un `DataTable` dans l'adresse (ARCHITECTURE § 10.1) : la recherche dans `?q=`, chaque
 * filtre dans son paramètre (`?fournisseur=12&statut=envoyee`). Copier le lien rouvre la même vue ;
 * fermer une fiche la rend telle quelle. « Effacer les filtres » retire filtres et recherche d'un
 * seul coup (deux écritures successives de l'adresse se marcheraient dessus).
 */
import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'

import { avecParametre } from '../../lib/adresse'
import type { Choix } from './filtrage'

export interface EtatTable {
  recherche: { valeur: string; onChange: (q: string) => void }
  choix: { valeurs: Choix; poser: (cle: string, valeur: string | null) => void; effacer: () => void }
}

export function useEtatTableAdresse(cles: readonly string[]): EtatTable {
  const [params, setParams] = useSearchParams()
  const signature = cles.join('|')
  const q = params.get('q') ?? ''
  const valeurs = useMemo(() => {
    const v: Record<string, string> = {}
    for (const c of signature.split('|')) {
      const lu = c ? params.get(c) : null
      if (lu) v[c] = lu
    }
    return v
  }, [params, signature])
  const onChange = useCallback(
    (texte: string) => setParams((p) => avecParametre(p, 'q', texte), { replace: true }),
    [setParams],
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
          for (const c of [...signature.split('|'), 'q']) if (c) suite.delete(c)
          return suite
        },
        { replace: true },
      ),
    [setParams, signature],
  )
  return { recherche: { valeur: q, onChange }, choix: { valeurs, poser, effacer } }
}
