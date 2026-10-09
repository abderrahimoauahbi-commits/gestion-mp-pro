/**
 * Une liste à onglets et ses fiches à onglets dans la même adresse (A5) : la liste range son onglet
 * dans `?onglet=` ; une fiche ouverte par-dessus prend `?onglet=` pour **son** volet, et la liste
 * garde le sien dans `?liste=`. Fermer la fiche rend la liste telle qu'on l'avait laissée (onglet,
 * recherche, filtres) — c'est ce que faisait F7 pour les qualités.
 */
import { useCallback } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'

/** Vrai si l'adresse est celle de la liste elle-même (pas d'une fiche par-dessus). */
const surLaListe = (pathname: string, base: string) => pathname === base

/** L'onglet de la liste, lu dans `?onglet=` sur la liste, dans `?liste=` sous une fiche. */
export function useOngletListe<T extends string>(
  base: string,
  permis: readonly T[],
  defaut: T,
): [T, (o: T) => void] {
  const { pathname } = useLocation()
  const [params, setParams] = useSearchParams()
  const cle = surLaListe(pathname, base) ? 'onglet' : 'liste'
  const actif = permis.find((p) => p === params.get(cle)) ?? defaut
  const choisir = useCallback(
    (o: T) =>
      setParams(
        (p) => {
          const s = new URLSearchParams(p)
          s.set(cle, o)
          return s
        },
        { replace: true },
      ),
    [setParams, cle],
  )
  return [actif, choisir]
}

/** Ouvrir une fiche (avec son volet), fermer vers la liste. `jetables` : paramètres propres à une fenêtre. */
export function useListeEtFiches(base: string, jetables: readonly string[] = []) {
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const depuisListe = surLaListe(pathname, base)
  const ouvrir = useCallback(
    (chemin: string, volet?: string, autres: Record<string, string> = {}) => {
      const p = new URLSearchParams(search)
      if (depuisListe) {
        const liste = p.get('onglet')
        p.delete('liste')
        if (liste) p.set('liste', liste)
      }
      p.delete('onglet')
      for (const j of jetables) p.delete(j)
      if (volet) p.set('onglet', volet)
      for (const [k, v] of Object.entries(autres)) p.set(k, v)
      const t = p.toString()
      navigate(`${chemin}${t ? `?${t}` : ''}`)
    },
    [navigate, search, depuisListe, jetables],
  )
  const fermer = useCallback(() => {
    const p = new URLSearchParams(search)
    const liste = depuisListe ? p.get('onglet') : p.get('liste')
    p.delete('onglet')
    p.delete('liste')
    for (const j of jetables) p.delete(j)
    if (liste) p.set('onglet', liste)
    const t = p.toString()
    navigate(`${base}${t ? `?${t}` : ''}`)
  }, [navigate, search, depuisListe, jetables, base])
  return { ouvrir, fermer }
}

/** Une valeur choisie parmi quelques-unes, dans `?<cle>=` (la valeur par défaut n'écrit rien). */
export function useChoixAdresse<T extends string>(
  cle: string,
  permises: readonly T[],
  defaut: T,
): [T, (v: T) => void] {
  const [params, setParams] = useSearchParams()
  const lue = params.get(cle)
  const valeur = permises.find((p) => p === lue) ?? defaut
  const choisir = useCallback(
    (v: T) =>
      setParams(
        (p) => {
          const s = new URLSearchParams(p)
          if (v === defaut) s.delete(cle)
          else s.set(cle, v)
          return s
        },
        { replace: true },
      ),
    [setParams, cle, defaut],
  )
  return [valeur, choisir]
}
