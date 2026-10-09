/**
 * Les lectures de la liste des dossiers paginée au serveur : l'aperçu (indicateurs, onglets, pied,
 * non répartis — route 250) et l'ensemble borné des dossiers clos (pour savoir si le dossier d'une
 * facture est clos, sans charger toute la liste). La liste elle-même se lit page par page
 * (`useListePaginee`).
 */
import { keepPreviousData } from '@tanstack/react-query'

import { useLecture } from '../../lib/requetes'
import type { Page } from '../../lib/types'
import type { ApercuDossiers, DossierResume } from './types'

type Params = Record<string, string | number | boolean | null | undefined>

/** L'aperçu du périmètre demandé : comptes par statut, totaux, non répartis, fournisseurs. */
export const useApercuDossiers = (params: Params) =>
  useLecture<ApercuDossiers>('/dossiers/apercu', params, { placeholderData: keepPreviousData })

/** Les identifiants des dossiers clos (bornés), pour bloquer un second camion sur un dossier clos. */
export function useClosIds(actif: boolean): Set<number> {
  const clos = useLecture<Page<DossierResume>>(
    '/dossiers',
    { statut: 'clos', limite: 5000 },
    { enabled: actif },
  )
  return new Set((clos.data?.elements ?? []).map((d) => d.id))
}
