/**
 * La session : qui est connecté, avec quel rôle, et le contexte de démarrage (GET /contexte,
 * API-PRO route 3 : moi, compteurs du menu, date de clôture, inventaires ouverts, société, état du
 * serveur pour la direction et l'administrateur) — en un appel, relu toutes les 3 minutes et après
 * chaque écriture (invalidation globale).
 *
 * `FournisseurSession` garde toutes les adresses connectées : sans session, il renvoie à
 * `/connexion?retour={adresse demandée}`, qui la rouvre après la connexion. Une session perdue en
 * cours de travail (expirée, compte désactivé, code changé ailleurs) renvoie à la connexion avec
 * le motif (P1-6, H-09) ; une déconnexion voulue, sans motif.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router'

import { EcranCentre } from '../composants/coque/EcranCentre'
import { Chargement } from '../composants/retour/Chargement'
import { Erreur } from '../composants/retour/Erreur'
import { api, SESSION_PERDUE } from './api'
import { useLecture } from './requetes'
import type { Contexte, Moi } from './types-coque'
import type { Role } from './types'

export interface Session {
  contexte: Contexte
  moi: Moi
  role: Role
  /** Ferme la session au serveur puis revient à la connexion (cache vidé là-bas). */
  deconnecter: () => Promise<void>
  /** Relit le contexte (après PUT /moi). */
  rafraichir: () => Promise<unknown>
}

const ContexteSession = createContext<Session | null>(null)

/** La session de l'écran ; hors d'une session, c'est une faute de programmation. */
export function useSession(): Session {
  const s = useContext(ContexteSession)
  if (!s) throw new Error('useSession hors de la session.')
  return s
}

/** La session si elle existe (composants posés aussi hors session : essais, pages publiques). */
export function useSessionSiOuverte(): Session | null {
  return useContext(ContexteSession)
}

/** Fournit une session donnée (essais, démonstration). */
export function SessionFournie({ session, children }: { session: Session; children: ReactNode }) {
  return <ContexteSession.Provider value={session}>{children}</ContexteSession.Provider>
}

/** Le texte qui dit pourquoi on revient à la connexion (motif du serveur, H-09). */
export function motifLisible(motif: string | null | undefined): string {
  const texte = (motif ?? '').trim()
  if (/plus actif/i.test(texte)) return 'Ce compte n’est plus actif : voyez la direction.'
  if (!texte || /^connectez-vous/i.test(texte)) return 'Votre session a expiré : reconnectez-vous.'
  return texte
}

/** L'adresse de la connexion qui rouvrira `adresse` ensuite. */
export function versConnexion(adresse: string): string {
  return adresse && adresse !== '/' ? `/connexion?retour=${encodeURIComponent(adresse)}` : '/connexion'
}

/** Le motif posé dans l'état de la navigation vers la connexion. */
export interface EtatConnexion {
  motif?: string
}

function useAdresseCourante(): string {
  const { pathname, search } = useLocation()
  return `${pathname}${search}`
}

/** Écoute la session perdue en cours de travail : retour à la connexion, avec le motif. */
function useSessionPerdue(ouverte: boolean, adresse: string) {
  const naviguer = useNavigate()
  useEffect(() => {
    if (!ouverte) return
    const perte = (e: Event) => {
      const motif = e instanceof CustomEvent && typeof e.detail?.motif === 'string' ? e.detail.motif : ''
      const etat: EtatConnexion = { motif: motifLisible(motif) }
      naviguer(versConnexion(adresse), { replace: true, state: etat })
    }
    window.addEventListener(SESSION_PERDUE, perte)
    return () => window.removeEventListener(SESSION_PERDUE, perte)
  }, [ouverte, adresse, naviguer])
}

/** Garde de toutes les adresses connectées : lit le contexte, ou renvoie à la connexion. */
export function FournisseurSession() {
  const lecture = useLecture<Contexte>('/contexte', undefined, { refetchInterval: 180_000 })
  const adresse = useAdresseCourante()
  const naviguer = useNavigate()
  useSessionPerdue(Boolean(lecture.data), adresse)
  const { refetch } = lecture
  const deconnecter = useCallback(async () => {
    try {
      await api.post('/deconnexion')
    } catch {
      /* déjà déconnecté, ou serveur injoignable : on revient à la connexion quoi qu'il arrive */
    }
    naviguer('/connexion', { replace: true })
  }, [naviguer])
  const contexte = lecture.data
  const session = useMemo<Session | null>(
    () =>
      contexte
        ? { contexte, moi: contexte.moi, role: contexte.moi.role, deconnecter, rafraichir: () => refetch() }
        : null,
    [contexte, deconnecter, refetch],
  )
  if (session) {
    return (
      <ContexteSession.Provider value={session}>
        <Outlet />
      </ContexteSession.Provider>
    )
  }
  if (lecture.error?.statut === 401) return <Navigate to={versConnexion(adresse)} replace />
  if (lecture.isError) {
    return (
      <EcranCentre>
        <Erreur erreur={lecture.error} onReessayer={() => void refetch()} />
      </EcranCentre>
    )
  }
  return <Chargement quoi="Gestion MP PRO" />
}
