/**
 * Importations & coût de revient (`/importations?onglet=ouverts|clos|rattacher`, ECRANS-PRO 5.1 à
 * 5.3) : en-tête (« Analyse du coût de revient », « Nouveau dossier »), indicateurs sur tous les
 * dossiers ouverts et clos (périmètre écrit, anomalie 5.9 ; frais non répartis à part, chaque dossier
 * ouvrable), trois onglets ; les fenêtres « Nouveau dossier » (`/dossiers/nouveau`) et la fiche
 * (`/dossiers/:id`) s'ouvrent par-dessus, à adresse stable. Direction et achats.
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { formule } from '../../lib/aide'
import type { ErreurApi } from '../../lib/api'
import { montantCourt, montantPrecis, nombre, part } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { EnAttente } from './EnAttente'
import { useEtatPage, type EtatPage } from './etatPage'
import { FicheDossier } from './FicheDossier'
import { ListeDossiers } from './ListeDossiers'
import { NonRepartis } from './NonRepartis'
import { NouveauDossier } from './NouveauDossier'
import {
  partCharges,
  SEUIL_NON_REPARTIS,
  type DossierResume,
  type EnAttente as Attente,
  type OngletPage,
} from './types'

const TITRE = 'Importations & coût de revient'
const SOUS =
  'Une facture, un dossier : la livraison et ses frais, répartis à la valeur ou au poids. La TVA reste hors du coût.'

type Lecture = UseQueryResult<DossierResume[], ErreurApi>

const somme = (ds: readonly DossierResume[], f: (d: DossierResume) => number) =>
  ds.reduce((s, d) => s + f(d), 0)

function IndicateursPage({ dossiers }: { dossiers: readonly DossierResume[] }) {
  const ouverts = dossiers.filter((d) => d.statut === 'ouvert').length
  const achat = somme(dossiers, (d) => d.marchandise_mad)
  const charges = somme(dossiers, (d) => d.charges_mad)
  const cout = somme(dossiers, (d) => d.revient_mad)
  const p = partCharges(charges, achat)
  const sans = dossiers
    .filter((d) => Math.abs(d.charges_non_reparties_mad) > SEUIL_NON_REPARTIS)
    .map((d) => ({ id: d.id, numero: d.numero, montant: d.charges_non_reparties_mad }))
  return (
    <Indicateurs libelle="Tous les dossiers, ouverts et clos (hors annulés)">
      <Kpi
        titre="Dossiers"
        valeur={nombre(dossiers.length)}
        detail={`dont ${nombre(ouverts)} ouvert(s) · hors annulés`}
        formule={formule('import_dossiers')}
      />
      <Kpi
        titre="Achat"
        valeur={montantCourt(achat, 'MAD')}
        exact={montantPrecis(achat, 'MAD')}
        detail="marchandise, en MAD"
        formule={formule('import_achat')}
      />
      <Kpi
        titre="Charges hors TVA"
        valeur={montantCourt(charges, 'MAD')}
        exact={montantPrecis(charges, 'MAD')}
        ton="attention"
        detail={
          <>
            {p == null ? 'toutes les charges sauf la TVA' : `${part(p)} de l’achat`}{' '}
            <NonRepartis dossiers={sans} />
          </>
        }
        formule={formule('import_charges')}
      />
      <Kpi
        titre="Coût hors TVA"
        valeur={montantCourt(cout, 'MAD')}
        exact={montantPrecis(cout, 'MAD')}
        ton="ok"
        detail="achat + charges, rendu usine"
        formule={formule('import_cout')}
      />
    </Indicateurs>
  )
}

interface OngletProps {
  page: EtatPage
  onglet: OngletPage
  dossiers: Lecture
  annules: Lecture
  attente: number
  clos: (id: number) => boolean
}

function Onglet({ page, onglet, dossiers, annules, attente, clos }: OngletProps) {
  if (onglet === 'rattacher') return <EnAttente page={page} clos={clos} />
  const voirAnnules = onglet === 'clos' && page.annules
  const lu = voirAnnules ? annules : dossiers
  const statut = voirAnnules ? 'annule' : onglet === 'clos' ? 'clos' : 'ouvert'
  return (
    <ListeDossiers
      statut={statut}
      lignes={(lu.data ?? []).filter((d) => d.statut === statut)}
      chargement={lu.isPending}
      etat={page.etat}
      ouvrir={(id) => page.ouvrir(id)}
      erreur={lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : undefined}
      enAttente={
        onglet === 'ouverts' ? { nombre: attente, voir: () => page.choisirOnglet('rattacher') } : undefined
      }
      bascule={
        onglet === 'clos'
          ? { annules: page.annules, choisir: (a) => page.ecrire('etat', a ? 'annules' : null) }
          : undefined
      }
    />
  )
}

/** « Analyse du coût de revient », « Nouveau dossier ». */
function Actions({ page }: { page: EtatPage }) {
  const navigate = useNavigate()
  return (
    <>
      <Bouton
        titre="Par matière, titrage, fournisseur, qualité… dans la page Analyse"
        onClick={() => navigate('/analyse?onglet=revient')}
      >
        Analyse du coût de revient
      </Bouton>
      <Bouton
        variante="principal"
        icone="plus"
        titre="Ouvrir le dossier d’une facture reçue"
        onClick={() => page.nouveauDossier()}
      >
        Nouveau dossier
      </Bouton>
    </>
  )
}

export default function Importations() {
  const page = useEtatPage()
  const dossiers = useLecture<DossierResume[]>('/dossiers')
  const annules = useLecture<DossierResume[]>('/dossiers', { statut: 'annule' }, { enabled: page.annules })
  const attente = useLecture<Attente>('/dossiers/a-rattacher')
  const tous = dossiers.data ?? []
  // Une fiche ouverte par un lien collé : la liste dessous montre l'onglet de son statut.
  const sousFiche = page.ficheId != null ? tous.find((d) => d.id === page.ficheId) : undefined
  const onglet: OngletPage = sousFiche?.statut === 'clos' && !page.surListe ? 'clos' : page.onglet
  const nAttente = (attente.data?.factures.length ?? 0) + (attente.data?.sans_facture.length ?? 0)
  const clos = (id: number) => tous.some((d) => d.id === id && d.statut === 'clos')
  return (
    <Page titre={TITRE}>
      <EnTete titre={TITRE} sous={SOUS} actions={<Actions page={page} />} />
      <IndicateursPage dossiers={tous} />
      <Onglets
        libelle="Dossiers d’importation"
        actif={onglet}
        onChange={page.choisirOnglet}
        onglets={[
          {
            cle: 'ouverts',
            libelle: 'Dossiers ouverts',
            compte: tous.filter((d) => d.statut === 'ouvert').length,
          },
          { cle: 'clos', libelle: 'Dossiers clos', compte: tous.filter((d) => d.statut === 'clos').length },
          { cle: 'rattacher', libelle: 'En attente de dossier', compte: attente.data ? nAttente : null },
        ]}
      />
      <Onglet
        page={page}
        onglet={onglet}
        dossiers={dossiers}
        annules={annules}
        attente={nAttente}
        clos={clos}
      />
      {page.nouveau ? <NouveauDossier page={page} clos={clos} /> : null}
      {page.ficheId != null ? <FicheDossier id={page.ficheId} onFermer={page.fermer} /> : null}
    </Page>
  )
}
