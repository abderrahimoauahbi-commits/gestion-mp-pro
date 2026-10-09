/**
 * La fenêtre d'un réglage ouverte par l'adresse, par-dessus sa liste : `?onglet=postes&poste=12`,
 * `?onglet=codes&code=nouveau`. Le volet de la fenêtre (« Historique ») vit dans `?volet=` :
 * `?onglet=` est déjà celui de la page Réglages. Ouvrir est une navigation (« Précédent » referme) ;
 * fermer retire la fiche et son volet, et garde le reste (onglet, recherche, filtres).
 */
import { useCallback } from 'react'
import { useSearchParams } from 'react-router'

import { avecParametre } from '../../../lib/adresse'

export type VoletReglage = 'fiche' | 'historique'

export interface FenetreAdresse {
  /** L'identifiant de la fiche ouverte, `null` si aucune (ou une nouvelle). */
  id: number | null
  /** Vrai sur `…=nouveau`. */
  nouveau: boolean
  volet: VoletReglage
  ouvrir: (cible: number | 'nouveau') => void
  fermer: () => void
  choisirVolet: (volet: VoletReglage) => void
}

export function useFenetreAdresse(cle: string): FenetreAdresse {
  const [params, setParams] = useSearchParams()
  const brut = params.get(cle)
  const ouvrir = useCallback(
    (cible: number | 'nouveau') =>
      setParams((p) => avecParametre(avecParametre(p, 'volet', null), cle, String(cible))),
    [setParams, cle],
  )
  const fermer = useCallback(
    () => setParams((p) => avecParametre(avecParametre(p, cle, null), 'volet', null)),
    [setParams, cle],
  )
  const choisirVolet = useCallback(
    (volet: VoletReglage) =>
      setParams((p) => avecParametre(p, 'volet', volet === 'fiche' ? null : volet), { replace: true }),
    [setParams],
  )
  return {
    id: brut && /^\d+$/.test(brut) ? Number(brut) : null,
    nouveau: brut === 'nouveau',
    volet: params.get('volet') === 'historique' ? 'historique' : 'fiche',
    ouvrir,
    fermer,
    choisirVolet,
  }
}
