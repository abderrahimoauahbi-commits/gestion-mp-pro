/**
 * L'application (ARCHITECTURE § 10.1) : un routeur de données (`createBrowserRouter`) alimenté par
 * le registre des écrans (`routes.ts`).
 *
 * - `/connexion`, `/installation`, `/enroler` : hors coque, publics.
 * - Tout le reste passe par la session (`FournisseurSession` : sans session → connexion, puis
 *   retour à l'adresse demandée) : `/` → accueil du rôle ; `/lot/:id` (QR) → fiche de l'atelier ou
 *   du bureau ; `/atelier/*` hors coque (téléphone) ; les autres écrans dans la `Coque`, chacun
 *   gardé par ses rôles (refus → accueil + bandeau) ; une adresse inconnue → accueil + bandeau.
 * - À la racine, une seule fois : `Messages` (toasts) et `GardeNavigation` (saisie en cours :
 *   « Précédent », liens et gestes de la coque retenus — c'est pour `useBlocker` qu'il faut un
 *   routeur de données).
 */
import { useState } from 'react'
import {
  createBrowserRouter,
  isRouteErrorResponse,
  Navigate,
  Outlet,
  RouterProvider,
  useRouteError,
  type RouteObject,
} from 'react-router'

import { Coque } from './composants/coque/Coque'
import { EcranCentre } from './composants/coque/EcranCentre'
import { GardeNavigation } from './composants/coque/GardeNavigation'
import { AdresseInconnue, GardeEcran, VersAccueil, VersLot } from './composants/coque/GardeEcran'
import { Messages } from './composants/retour/Messages'
import { Note } from './composants/retour/Note'
import { Bouton } from './composants/saisie/Bouton'
import { FournisseurSession } from './lib/session'
import Connexion from './pages/connexion/Connexion'
import Enroler from './pages/connexion/Enroler'
import Installation from './pages/connexion/Installation'
import { appliquerTheme, imprimerEnClair } from './pages/compte/theme'
import { ECRANS, type Ecran } from './routes'
import './styles/impression.css'

appliquerTheme()
imprimerEnClair()

/** La racine : la page, les messages, la garde de saisie. */
function Racine() {
  return (
    <>
      <Outlet />
      <Messages />
      <GardeNavigation />
    </>
  )
}

/** Une page tombée en erreur au rendu : dite, avec de quoi repartir (jamais une page blanche). */
function PanneEcran() {
  const erreur = useRouteError()
  const texte = isRouteErrorResponse(erreur)
    ? `${erreur.status} ${erreur.statusText}`
    : erreur instanceof Error
      ? erreur.message
      : 'Erreur inattendue.'
  return (
    <EcranCentre>
      <Note ton="critique">
        L’écran a rencontré une erreur : {texte} Rechargez la page ; si l’erreur revient, notez ce que vous
        faisiez.
      </Note>
      <Bouton variante="principal" onClick={() => window.location.reload()}>
        Recharger la page
      </Bouton>
    </EcranCentre>
  )
}

/** La route d'un écran du registre : gardée par ses rôles, page chargée à la demande. */
function routeDe(ecran: Ecran): RouteObject {
  return { path: ecran.chemin, handle: { ecran }, element: <GardeEcran ecran={ecran} /> }
}

/** Toutes les routes de l'application (le routeur du navigateur, ou celui des essais). */
export function creerRoutes(ecrans: readonly Ecran[] = ECRANS): RouteObject[] {
  return [
    {
      element: <Racine />,
      errorElement: <PanneEcran />,
      children: [
        { path: '/connexion', element: <Connexion /> },
        { path: '/installation', element: <Installation /> },
        { path: '/enroler', element: <Enroler /> },
        { path: '/guide', element: <Navigate to="/aide" replace /> },
        {
          element: <FournisseurSession />,
          children: [
            { path: '/', element: <VersAccueil /> },
            { path: '/lot/:id', element: <VersLot /> },
            ...ecrans.filter((e) => e.atelier).map(routeDe),
            {
              element: <Coque />,
              children: [
                ...ecrans.filter((e) => !e.atelier).map(routeDe),
                { path: '*', element: <AdresseInconnue /> },
              ],
            },
          ],
        },
      ],
    },
  ]
}

export default function App() {
  const [routeur] = useState(() => createBrowserRouter(creerRoutes()))
  return <RouterProvider router={routeur} />
}
