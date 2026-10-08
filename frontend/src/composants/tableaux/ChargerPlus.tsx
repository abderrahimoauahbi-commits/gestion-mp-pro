/**
 * Les longues listes paginées au serveur (A2 : mouvements, journal, opérations…) : pas de
 * pagination visuelle, le tableau défile dans son cadre ; à la fin, « Charger les 500 suivants »
 * (ou « les N derniers »), et ce qui est chargé sur le total. `useListePaginee` lit les pages
 * `Page[T]` (`{elements, total, suivant}`, curseur `?apres=`) avec la recherche et les filtres
 * envoyés au serveur.
 */
import { useInfiniteQuery } from '@tanstack/react-query'

import { api, type ErreurApi } from '../../lib/api'
import { nombre } from '../../lib/format'
import { cleApi } from '../../lib/requetes'
import type { Page } from '../../lib/types'
import { Bouton } from '../saisie/Bouton'
import styles from './ChargerPlus.module.css'

/** La taille d'une page du serveur (API-PRO § 0.1). */
export const TAILLE_PAGE = 500

export interface ChargerPlusProps {
  charges: number
  total: number
  onCharger: () => unknown
  occupe?: boolean
}

/** Le libellé du bouton : « Charger les 500 suivants », ou « les 12 derniers ». */
export function libelleChargerPlus(charges: number, total: number): string {
  const reste = total - charges
  if (reste > TAILLE_PAGE) return `Charger les ${nombre(TAILLE_PAGE)} suivants`
  return reste === 1 ? 'Charger le dernier' : `Charger les ${nombre(reste)} derniers`
}

export function ChargerPlus({ charges, total, onCharger, occupe }: ChargerPlusProps) {
  if (charges >= total) return null
  return (
    <div className={styles.chargerPlus}>
      <span>
        {nombre(charges)} lignes chargées sur {nombre(total)}
      </span>
      <Bouton taille="petit" occupe={occupe} attente="Chargement…" onClick={onCharger}>
        {libelleChargerPlus(charges, total)}
      </Bouton>
    </div>
  )
}

type Parametres = Record<string, string | number | boolean | null | undefined>

/** Les pages d'une longue liste, à la demande : lignes, total, et de quoi charger la suite. */
export function useListePaginee<T>(chemin: string, parametres: Parametres = {}) {
  const requete = useInfiniteQuery<Page<T>, ErreurApi>({
    queryKey: [...cleApi(chemin, parametres), 'pages'],
    queryFn: ({ pageParam, signal }) =>
      api.get<Page<T>>(
        chemin,
        { ...parametres, apres: typeof pageParam === 'string' ? pageParam : undefined },
        signal,
      ),
    initialPageParam: null,
    getNextPageParam: (derniere) => derniere.suivant,
  })
  const pages = requete.data?.pages ?? []
  const lignes = pages.flatMap((p) => p.elements)
  const total = pages[0]?.total ?? 0
  const chargerPlus: ChargerPlusProps = {
    charges: lignes.length,
    total,
    occupe: requete.isFetchingNextPage,
    onCharger: () => requete.fetchNextPage(),
  }
  return { requete, lignes, total, chargerPlus }
}
