/**
 * « Réglages » (`/reglages?onglet=parametres|devises|magasins|postes|codes|periode`), ECRANS-PRO
 * partie 8 : la partie métier des réglages. La direction écrit tout ; les achats écrivent les
 * devises et lisent le reste ; l'alimentation et l'administrateur sont refusés par la garde.
 *
 * Les brouillons des Paramètres et des Devises vivent **ici** : changer d'onglet ne les perd pas,
 * l'onglet porte « • » tant qu'ils ne sont pas enregistrés, et quitter la page le demande (P8-8,
 * H-10). « Postes de frais » et « Codes douaniers » sont réalisés par le lot F5
 * (`pages/importations/reglages/`). Changer d'onglet repart d'une adresse nette (chaque onglet a
 * ses propres critères).
 */
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { useGardeSaisie } from '../../composants/coque/garde'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { useOngletAdresse } from '../../lib/adresse'
import { ongletsPermis } from '../../lib/droits'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { ECRANS } from '../../routes'
import { CodesDouaniers } from '../importations/reglages/CodesDouaniers'
import { PostesFrais } from '../importations/reglages/PostesFrais'
import {
  BROUILLON_DEVISES_VIDE,
  deviseSale,
  Devises,
  type BrouillonDevises,
  type DeviseFiche,
} from './Devises'
import { Magasins, type MagasinFiche } from './Magasins'
import { HistoriqueParametres } from './parametres/HistoriqueParametres'
import type { Brouillon, Reglage } from './parametres/logique'
import { Parametres } from './parametres/Parametres'
import { PeriodeClose } from './PeriodeClose'

/** La phrase sous le titre, onglet par onglet. */
export const PHRASES: Readonly<Record<string, string>> = {
  parametres:
    'Les seuils et les marges qui règlent le calcul : chaque changement recalcule tout le pilotage.',
  devises: 'Le cours de chaque devise, en MAD pour une unité, daté et gardé à chaque changement.',
  magasins: 'Les magasins de stock courant et de quarantaine, et ce qu’ils détiennent.',
  postes: 'Les frais d’un dossier d’importation, et comment ils se répartissent.',
  codes: 'La position du tarif douanier de chaque matière, et son taux de droits.',
  periode: 'La date jusqu’à laquelle rien ne s’écrit plus.',
}

function Contenu({ onglet, brouillons }: { onglet: string; brouillons: Brouillons }) {
  const { role } = useSession()
  const direction = role === 'direction'
  const parametres = useLecture<Reglage[]>('/parametres')
  const devises = useLecture<DeviseFiche[]>('/devises')
  const magasins = useLecture<MagasinFiche[]>('/magasins')
  const [historique, setHistorique] = useState(false)
  if (onglet === 'postes') return <PostesFrais />
  if (onglet === 'codes') return <CodesDouaniers />
  const lu = onglet === 'devises' ? devises : onglet === 'magasins' ? magasins : parametres
  if (lu.isPending) return <Chargement quoi="les réglages" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  if (onglet === 'devises') {
    return <Devises devises={devises.data ?? []} b={brouillons.devises} onB={brouillons.poserDevises} ecrit />
  }
  if (onglet === 'magasins') return <Magasins magasins={magasins.data ?? []} ecrit={direction} />
  if (onglet === 'periode') {
    return (
      <PeriodeClose reglage={parametres.data?.find((r) => r.cle === 'date_cloture')} direction={direction} />
    )
  }
  return (
    <>
      <Parametres
        reglages={parametres.data ?? []}
        brouillon={brouillons.parametres}
        onBrouillon={brouillons.poserParametres}
        ecrit={direction}
        onHistorique={direction ? () => setHistorique(true) : undefined}
      />
      {historique ? <HistoriqueParametres onFermer={() => setHistorique(false)} /> : null}
    </>
  )
}

interface Brouillons {
  parametres: Brouillon
  poserParametres: (b: Brouillon) => void
  devises: BrouillonDevises
  poserDevises: (b: BrouillonDevises) => void
}

export default function Reglages() {
  const { role } = useSession()
  const [, setParams] = useSearchParams()
  const ecran = ECRANS.find((e) => e.chemin === '/reglages')
  const permis = ecran ? ongletsPermis(ecran, role) : []
  const [onglet] = useOngletAdresse(
    permis.map((o) => o.cle),
    'parametres',
  )
  const [parametres, poserParametres] = useState<Brouillon>({})
  const [devises, poserDevises] = useState<BrouillonDevises>(BROUILLON_DEVISES_VIDE)
  const sales: Record<string, boolean> = {
    parametres: Object.keys(parametres).length > 0,
    devises: deviseSale(devises),
  }
  useGardeSaisie(Object.values(sales).some(Boolean))
  return (
    <Page titre="Réglages">
      <EnTete
        titre="Réglages"
        sous={PHRASES[onglet]}
        actions={
          role === 'direction' ? (
            <Link
              to="/metiers"
              title="Les métiers à tisser, leurs réglages et les fils montés : une page à part"
            >
              Métiers à tisser →
            </Link>
          ) : null
        }
      />
      <Onglets
        libelle="Onglets des réglages"
        actif={onglet}
        onChange={(o) => setParams(o === 'parametres' ? {} : { onglet: o }, { replace: true })}
        onglets={permis.map((o) => ({ cle: o.cle, libelle: o.libelle, court: o.court, sale: sales[o.cle] }))}
      />
      <Contenu onglet={onglet} brouillons={{ parametres, poserParametres, devises, poserDevises }} />
    </Page>
  )
}
