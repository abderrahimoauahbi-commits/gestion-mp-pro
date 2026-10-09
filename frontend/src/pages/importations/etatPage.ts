/**
 * L'état de la page des importations, dans l'adresse (A5, anomalie 5.16).
 *
 * - Sur `/importations` : `?onglet=ouverts|clos|rattacher`, `&etat=annules` (onglet des clos),
 *   `&q=`, `&fournisseur=`, `&verifier=` (liste), `&vue=factures|receptions`, `&locaux=1`.
 * - Une fiche (`/dossiers/:id?onglet=…`) ou le nouveau dossier (`/dossiers/nouveau?onglet=…`) ont
 *   leur propre `?onglet=` et `?q=` : l'adresse de la liste d'où on les a ouverts voyage dans
 *   l'état de navigation (`state.retour`), et la liste dessous se lit dans cette adresse, figée.
 *   Fermer y revient (filtres gardés) ; ouverte d'ailleurs (l'analyse), la fiche y ramène ; ouverte
 *   par un lien collé, elle revient à l'onglet de son statut.
 */
import { useCallback, useMemo } from 'react'
import { useLocation, useNavigate, useParams, useSearchParams } from 'react-router'

import { avecParametre } from '../../lib/adresse'
import { ONGLETS_PAGE, type OngletPage } from './types'

export interface EtatListe {
  recherche: { valeur: string; onChange: (q: string) => void }
  choix: {
    valeurs: Readonly<Record<string, string | undefined>>
    poser: (cle: string, valeur: string | null) => void
    effacer: () => void
  }
}

const FILTRES_LISTE = ['fournisseur', 'verifier'] as const

const estOnglet = (v: string | null): v is OngletPage => ONGLETS_PAGE.some((o) => o === v)

/** Le `state.retour` d'une navigation, s'il est une adresse de l'application. */
export function retourDe(state: unknown): string | null {
  if (typeof state !== 'object' || state === null || !('retour' in state)) return null
  const r = state.retour
  return typeof r === 'string' && r.startsWith('/') ? r : null
}

/** Ouvrir, remplacer, créer, fermer : la liste d'où l'on vient voyage dans `state.retour`. */
function useNavigations(retour: string | null, adresseListe: string | null) {
  const navigate = useNavigate()
  return {
    ouvrir: (dossierId: number, volet?: string) =>
      navigate(`/dossiers/${dossierId}${volet ? `?onglet=${volet}` : ''}`, {
        state: { retour: adresseListe ?? '/importations' },
      }),
    /** Après une création : la fiche remplace la fenêtre de création (Précédent ne la rouvre pas). */
    remplacerPar: (dossierId: number, volet?: string) =>
      navigate(`/dossiers/${dossierId}${volet ? `?onglet=${volet}` : ''}`, {
        replace: true,
        state: { retour: retour ?? '/importations' },
      }),
    nouveauDossier: (volet?: 'facture' | 'main') =>
      navigate(`/dossiers/nouveau${volet ? `?onglet=${volet}` : ''}`, {
        state: { retour: adresseListe ?? '/importations' },
      }),
    /** Fermer une fenêtre : retour d'où l'on venait, sinon l'onglet du statut du dossier. */
    fermer: (statut?: string | null) =>
      navigate(
        retour ??
          (statut === 'clos'
            ? '/importations?onglet=clos'
            : statut === 'annule'
              ? '/importations?onglet=clos&etat=annules'
              : '/importations'),
      ),
  }
}

export function useEtatPage() {
  const { pathname, search, state } = useLocation()
  const { id } = useParams()
  const [params, setParams] = useSearchParams()
  const surListe = pathname === '/importations'
  const nouveau = pathname === '/dossiers/nouveau'
  const ficheId = !surListe && !nouveau && id && /^\d+$/.test(id) ? Number(id) : null
  const retour = retourDe(state)
  const liste = useMemo(() => {
    if (surListe) return params
    const venu = retour?.startsWith('/importations') ? (retour.split('?')[1] ?? '') : ''
    return new URLSearchParams(venu)
  }, [surListe, params, retour])
  const ecrire = useCallback(
    (cle: string, valeur: string | null) => {
      if (surListe) setParams((p) => avecParametre(p, cle, valeur), { replace: true })
    },
    [surListe, setParams],
  )
  const lu = liste.get('onglet')
  const onglet: OngletPage = estOnglet(lu) ? lu : 'ouverts'
  const etat: EtatListe = {
    recherche: { valeur: liste.get('q') ?? '', onChange: (q) => ecrire('q', q) },
    choix: {
      valeurs: Object.fromEntries(FILTRES_LISTE.map((c) => [c, liste.get(c) ?? undefined])),
      poser: ecrire,
      effacer: () => {
        if (!surListe) return
        setParams(
          (p) => {
            const suite = new URLSearchParams(p)
            for (const c of [...FILTRES_LISTE, 'q']) suite.delete(c)
            return suite
          },
          { replace: true },
        )
      },
    },
  }
  const ici = `${pathname}${search}`
  const adresseListe = surListe ? ici : (retour ?? null)
  return {
    surListe,
    nouveau,
    ficheId,
    onglet,
    /** L'onglet des clos montre les annulés. */
    annules: liste.get('etat') === 'annules',
    vue: liste.get('vue'),
    locaux: liste.get('locaux') === '1',
    etat,
    ecrire,
    choisirOnglet: (o: OngletPage) =>
      setParams((p) => avecParametre(avecParametre(p, 'onglet', o === 'ouverts' ? null : o), 'etat', null), {
        replace: true,
      }),
    ...useNavigations(retour, adresseListe),
  }
}

export type EtatPage = ReturnType<typeof useEtatPage>
