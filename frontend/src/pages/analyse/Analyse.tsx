/**
 * « Analyse » (`/analyse?onglet=valorisation|matrice|historique|opportunites|fournisseurs|revient|
 * echeancier|controles|production`), ECRANS-PRO partie 8 : une question par onglet. Direction et
 * achats ; l'alimentation et l'administrateur sont refusés par la garde (`EcranReserve`).
 *
 * Défaut : la Valorisation pour la direction, la Matrice pour les achats ; `?onglet=prix` (ancienne
 * adresse de Gestion MP) mène à la Matrice. Les compteurs des onglets viennent des mêmes lectures
 * que les onglets (cache partagé, P8-26). Le « Coût de revient » est réalisé par le lot F5
 * (`pages/importations/revient/AnalyseRevient.tsx`) et monté ici.
 * L'en-tête porte « Bilan du mois » (direction et achats, P8-24).
 */
import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { useOngletAdresse } from '../../lib/adresse'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import { ECRANS } from '../../routes'
import AnalyseRevient from '../importations/revient/AnalyseRevient'
import styles from './analyse.module.css'
import { BilanDuMois } from './BilanDuMois'
import { Controles } from './controles/Controles'
import { useControles, useHistoriquePrix, useMatrice, useOpportunites } from './donnees'
import { Echeancier } from './echeancier/Echeancier'
import { Fournisseurs } from './Fournisseurs'
import { Opportunites } from './Opportunites'
import { Matrice } from './prix/Matrice'
import { PrixPayes } from './prix/PrixPayes'
import { Production } from './Production'
import { Valorisation } from './Valorisation'

/** La phrase sous le titre, onglet par onglet (ECRANS-PRO partie 8, « 9 phrases exactes »). */
export const PHRASES: Readonly<Record<string, string>> = {
  valorisation:
    'Ce que vaut le stock détenu — magasins et métiers —, au coût moyen pondéré des achats réels.',
  matrice: 'Le prix de chaque matière, mois par mois, dans la monnaie de la facture.',
  historique: 'Chaque prix payé, face au précédent de la même matière chez le même fournisseur.',
  opportunites: 'Les matières comparables qui s’achètent moins cher ailleurs, à la même époque.',
  fournisseurs: 'Les fournisseurs notés sur leurs livraisons : à l’heure, complètes, conformes.',
  revient: 'Ce que la matière importée a coûté, rendue usine.',
  echeancier: 'Ce qu’il faudra payer, et quand : factures des fournisseurs et frais d’importation.',
  controles: 'Les contrôles de cohérence des données, et quoi faire pour chacun.',
  production: 'Le sorti net de chaque ordre de fabrication, face au prévu par la recette.',
}

function useCompteurs(): Partial<Record<string, number>> {
  const matrice = useMatrice()
  const historique = useHistoriquePrix()
  const opportunites = useOpportunites()
  const controles = useControles()
  return {
    matrice: matrice.data?.lignes.length,
    historique: historique.data?.lignes.length,
    opportunites: opportunites.data?.lignes.length,
    controles: controles.data?.synthese.a_corriger,
  }
}

function Contenu({ onglet }: { onglet: string }) {
  switch (onglet) {
    case 'valorisation':
      return <Valorisation />
    case 'matrice':
      return <Matrice />
    case 'historique':
      return <PrixPayes />
    case 'opportunites':
      return <Opportunites />
    case 'fournisseurs':
      return <Fournisseurs />
    case 'echeancier':
      return <Echeancier />
    case 'controles':
      return <Controles />
    case 'production':
      return <Production />
    default:
      return <AnalyseRevient />
  }
}

/** Sous le titre : la phrase de l'onglet, et les liens vers les bobines et les pesées. */
function SousTitre({ onglet }: { onglet: string }) {
  return (
    <>
      {PHRASES[onglet]} · Réceptions :{' '}
      <Link
        to="/receptions?onglet=bobines"
        title="Le poids moyen des bobines, matière par matière, au fil des réceptions"
      >
        bobines
      </Link>{' '}
      ·{' '}
      <Link to="/receptions?onglet=pesees" title="Chaque pesée face au bon de livraison">
        pesées
      </Link>
    </>
  )
}

export default function Analyse() {
  const { role } = useSession()
  const [params, setParams] = useSearchParams()
  const ecran = ECRANS.find((e) => e.chemin === '/analyse')
  const permis = ecran ? ongletsPermis(ecran, role) : []
  const cles = permis.map((o) => o.cle)
  const defaut = role === 'achats' ? 'matrice' : 'valorisation'
  const [onglet] = useOngletAdresse(cles, defaut)
  // Chaque onglet a ses propres critères : en changer repart d'une adresse nette (le coût de
  // revient et les fournisseurs lisent tous deux `fournisseur`, par exemple).
  const choisir = (o: string) => setParams(o === defaut ? {} : { onglet: o }, { replace: true })
  const compteurs = useCompteurs()
  const ancien = params.get('onglet') === 'prix'
  useEffect(() => {
    if (ancien) setParams({ onglet: 'matrice' }, { replace: true })
  }, [ancien, setParams])
  return (
    <Page titre="Analyse">
      <EnTete
        titre="Analyse"
        sous={<SousTitre onglet={onglet} />}
        actions={
          <span className={styles.rangee}>
            <BilanDuMois />
          </span>
        }
      />
      <Onglets
        libelle="Onglets de l’analyse"
        actif={onglet}
        onChange={choisir}
        onglets={permis.map((o) => ({
          cle: o.cle,
          libelle: o.libelle,
          court: o.court,
          compte: compteurs[o.cle],
        }))}
      />
      <Contenu onglet={onglet} />
    </Page>
  )
}
