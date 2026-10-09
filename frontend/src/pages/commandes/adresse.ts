/**
 * Une liste à onglets et ses fiches à onglets dans la même adresse (A5) : la liste range son onglet
 * dans `?onglet=` ; une fiche ouverte par-dessus prend `?onglet=` pour **son** volet, et la liste
 * garde le sien dans `?liste=`. Fermer la fiche rend la liste telle qu'on l'avait laissée (onglet,
 * recherche, filtres) — c'est ce que faisait F7 pour les qualités.
 */
import { useCallback, useState } from 'react'
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

/** L'adresse où ramène la fermeture d'une fiche ouverte d'ailleurs (`state.retour`, le Cockpit…). */
export function retourDe(state: unknown): string | null {
  if (typeof state !== 'object' || state == null || !('retour' in state)) return null
  const r = state.retour
  return typeof r === 'string' && r.startsWith('/') ? r : null
}

/**
 * Ouvrir une fiche (avec son volet), fermer vers la liste. `jetables` : paramètres propres à une
 * fenêtre. Une fiche ouverte d'un autre écran avec `state.retour` (« Examiner » du Cockpit) y
 * revient en se fermant, même après un changement de volet.
 */
export function useListeEtFiches(base: string, jetables: readonly string[] = []) {
  const navigate = useNavigate()
  const { pathname, search, state } = useLocation()
  const depuisListe = surLaListe(pathname, base)
  // Retenu tant que la fiche reste ouverte : un changement de volet (`?onglet=`) perd l'état.
  const lu = retourDe(state)
  const [retenu, setRetenu] = useState<string | null>(lu)
  if (lu && lu !== retenu) setRetenu(lu)
  if (!lu && depuisListe && retenu) setRetenu(null)
  const retour = lu ?? (depuisListe ? null : retenu)
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
      navigate(`${chemin}${t ? `?${t}` : ''}`, { state: retour ? { retour } : undefined })
    },
    [navigate, search, depuisListe, jetables, retour],
  )
  const fermer = useCallback(() => {
    if (retour) {
      navigate(retour)
      return
    }
    const p = new URLSearchParams(search)
    const liste = depuisListe ? p.get('onglet') : p.get('liste')
    p.delete('onglet')
    p.delete('liste')
    for (const j of jetables) p.delete(j)
    if (liste) p.set('onglet', liste)
    const t = p.toString()
    navigate(`${base}${t ? `?${t}` : ''}`)
  }, [navigate, search, depuisListe, jetables, base, retour])
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
