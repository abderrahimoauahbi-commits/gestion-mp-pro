/**
 * « Administration » (`/administration?onglet=comptes|appareils|sauvegardes|journal|courriel|serveur|
 * telephone|technique|reprise|donnees`), ECRANS-PRO partie 8 : la partie technique des réglages.
 * Direction et administrateur technique ; l'administrateur n'y voit **aucune donnée métier** (pas
 * d'aperçu chiffré du courriel, pas de données brutes, prix vidés du journal par le serveur).
 * Changer d'onglet repart d'une adresse nette.
 */
import { useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Vide } from '../../composants/retour/Vide'
import { useOngletAdresse } from '../../lib/adresse'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import { ECRANS } from '../../routes'
import { Appareils } from './Appareils'
import { Comptes } from './Comptes'
import { CourrielDuLundi } from './Courriel'
import { DonneesBrutes } from './DonneesBrutes'
import { Journal } from './Journal'
import { Sauvegardes } from './Sauvegardes'
import { Serveur } from './Serveur'
import { Technique } from './Technique'
import { Telephone } from './Telephone'

/** La phrase sous le titre, onglet par onglet (ECRANS-PRO partie 8). */
export const PHRASES: Readonly<Record<string, string>> = {
  comptes: 'Qui se connecte, avec quel rôle et quel code.',
  appareils: 'Les appareils enrôlés qui ouvrent l’écran de connexion.',
  sauvegardes: 'Les copies de la base : leur état, leur conservation, en faire une, revenir à l’une d’elles.',
  journal: 'Qui a fait quoi, sur quoi, et quand — filtré et exportable.',
  courriel: 'La synthèse de la semaine envoyée chaque lundi : à qui, et ce qu’elle dirait aujourd’hui.',
  serveur: 'La version, la base, les sauvegardes, l’adresse sur le réseau et qui est connecté.',
  telephone: 'Ouvrir Gestion MP PRO sur un téléphone, dans l’usine ou en dehors.',
  technique: 'Les réglages techniques : l’adresse publique du serveur.',
  reprise: 'Le miroir de Gestion MP : son état et son rafraîchissement.',
  donnees: 'Les lignes brutes d’une table, pour vérifier un chiffre par un autre chemin.',
}

function Contenu({ onglet }: { onglet: string }) {
  switch (onglet) {
    case 'appareils':
      return <Appareils />
    case 'sauvegardes':
      return <Sauvegardes />
    case 'journal':
      return <Journal />
    case 'courriel':
      return <CourrielDuLundi />
    case 'serveur':
      return <Serveur />
    case 'telephone':
      return <Telephone />
    case 'technique':
      return <Technique />
    case 'donnees':
      return <DonneesBrutes />
    case 'reprise':
      return (
        <Carte remplir>
          <Vide>
            L’état du miroir de Gestion MP arrive avec la route de la reprise (`GET /reprise`, API-PRO 243),
            pas encore servie : en attendant, la reprise se lance sur le serveur (`make miroir`).
          </Vide>
        </Carte>
      )
    default:
      return <Comptes />
  }
}

export default function Administration() {
  const { role } = useSession()
  const [, setParams] = useSearchParams()
  const ecran = ECRANS.find((e) => e.chemin === '/administration')
  const permis = ecran ? ongletsPermis(ecran, role) : []
  const [onglet] = useOngletAdresse(
    permis.map((o) => o.cle),
    'comptes',
  )
  return (
    <Page titre="Administration">
      <EnTete titre="Administration" sous={PHRASES[onglet]} />
      <Onglets
        libelle="Onglets de l’administration"
        actif={onglet}
        onChange={(o) => setParams(o === 'comptes' ? {} : { onglet: o }, { replace: true })}
        onglets={permis.map((o) => ({ cle: o.cle, libelle: o.libelle, court: o.court }))}
      />
      <Contenu onglet={onglet} />
    </Page>
  )
}
