/**
 * La garde des adresses connectées, dérivée du registre : un écran refusé au rôle (ou un onglet
 * refusé) ramène à l'accueil du rôle avec le bandeau « réservé à un autre rôle » ; une adresse
 * inconnue, avec « n'existe pas ». `/` mène à l'accueil du rôle ; `/lot/:id` (étiquette QR) à la
 * fiche de l'atelier au téléphone pour l'alimentation, à la fiche du bureau sinon (P1-3, H-08).
 */
import { lazy, Suspense, type ComponentType, type LazyExoticComponent } from 'react'
import { Navigate, useLocation, useParams } from 'react-router'

import { accueilDe, estTelephone, refus } from '../../lib/droits'
import { useSession } from '../../lib/session'
import type { Ecran } from '../../routes'
import { Chargement } from '../retour/Chargement'
import type { EtatRefus } from './EcranReserve'

const pages = new Map<Ecran, LazyExoticComponent<ComponentType>>()

/** La page d'un écran, chargée à la demande (une seule fois par écran). */
export function pageDe(ecran: Ecran): LazyExoticComponent<ComponentType> {
  let page = pages.get(ecran)
  if (!page) {
    page = lazy(ecran.page)
    pages.set(ecran, page)
  }
  return page
}

export function GardeEcran({ ecran }: { ecran: Ecran }) {
  const { role } = useSession()
  const { pathname, search } = useLocation()
  const adresse = `${pathname}${search}`
  const raison = refus(role, adresse)
  if (raison) {
    const etat: EtatRefus = raison === 'inconnue' ? { inconnue: adresse } : { refuse: adresse }
    return <Navigate to={accueilDe(role)} replace state={etat} />
  }
  const Page = pageDe(ecran)
  return (
    <Suspense fallback={<Chargement quoi="l’écran" />}>
      <Page />
    </Suspense>
  )
}

/** `/` : l'accueil du rôle. */
export function VersAccueil() {
  const { role } = useSession()
  return <Navigate to={accueilDe(role)} replace />
}

/** `/lot/:id` (l'adresse des étiquettes QR) : la fiche du lot qui convient à l'appareil et au rôle. */
export function VersLot() {
  const { role } = useSession()
  const { id } = useParams()
  const atelier = role === 'alimentation' && estTelephone()
  return <Navigate to={atelier ? `/atelier/lots/${id}` : `/lots/${id}`} replace />
}

/** Une adresse qu'aucun écran ne sert : l'accueil, avec le bandeau. */
export function AdresseInconnue() {
  const { role } = useSession()
  const { pathname, search } = useLocation()
  const etat: EtatRefus = { inconnue: `${pathname}${search}` }
  return <Navigate to={accueilDe(role)} replace state={etat} />
}
