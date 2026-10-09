/**
 * Importations & coût de revient (`/importations?onglet=ouverts|clos|rattacher`, ECRANS-PRO 5.1 à
 * 5.3) : en-tête (« Analyse du coût de revient », « Nouveau dossier »), indicateurs sur tous les
 * dossiers ouverts et clos (périmètre écrit, anomalie 5.9 ; frais non répartis à part, chaque dossier
 * ouvrable), trois onglets ; les fenêtres « Nouveau dossier » (`/dossiers/nouveau`) et la fiche
 * (`/dossiers/:id`) s'ouvrent par-dessus, à adresse stable. Direction et achats. Les listes sont
 * **paginées au serveur** ; indicateurs, onglets, pied et non répartis viennent de l'aperçu (route
 * 250) : mêmes chiffres qu'avant, sans charger toute la liste.
 */
import { useNavigate } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { formule } from '../../lib/aide'
import { montantCourt, montantPrecis, nombre, part } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useApercuDossiers, useClosIds } from './donnees'
import { EnAttente } from './EnAttente'
import { useEtatPage, type EtatPage } from './etatPage'
import { FicheDossier } from './FicheDossier'
import { ListeDossiers } from './ListeDossiers'
import { NonRepartis } from './NonRepartis'
import { NouveauDossier } from './NouveauDossier'
import {
  partCharges,
  type ApercuDossiers,
  type DossierFiche,
  type EnAttente as Attente,
  type OngletPage,
} from './types'

const TITRE = 'Importations & coût de revient'
const SOUS =
  'Une facture, un dossier : la livraison et ses frais, répartis à la valeur ou au poids. La TVA reste hors du coût.'

function IndicateursPage({ apercu }: { apercu?: ApercuDossiers }) {
  const achat = apercu?.marchandise_mad ?? 0
  const charges = apercu?.charges_mad ?? 0
  const cout = apercu?.revient_mad ?? 0
  const p = partCharges(charges, achat)
  const sans = (apercu?.non_repartis ?? []).map((d) => ({ id: d.id, numero: d.numero, montant: d.montant }))
  return (
    <Indicateurs libelle="Tous les dossiers, ouverts et clos (hors annulés)">
      <Kpi
        titre="Dossiers"
        valeur={nombre(apercu?.nombre ?? 0)}
        detail={`dont ${nombre(apercu?.ouvert ?? 0)} ouvert(s) · hors annulés`}
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

function Onglet({
  page,
  onglet,
  attente,
  clos,
}: {
  page: EtatPage
  onglet: OngletPage
  attente: number
  clos: (id: number) => boolean
}) {
  if (onglet === 'rattacher') return <EnAttente page={page} clos={clos} />
  const voirAnnules = onglet === 'clos' && page.annules
  const statut = voirAnnules ? 'annule' : onglet === 'clos' ? 'clos' : 'ouvert'
  return (
    <ListeDossiers
      statut={statut}
      etat={page.etat}
      ouvrir={(id) => page.ouvrir(id)}
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
  const apercu = useApercuDossiers({})
  const attente = useLecture<Attente>('/dossiers/a-rattacher')
  const closIds = useClosIds(page.onglet === 'rattacher' || page.nouveau)
  const clos = (id: number) => closIds.has(id)
  // Une fiche ouverte par un lien collé : la liste dessous montre l'onglet de son statut.
  const sousFiche = useLecture<DossierFiche>(page.ficheId != null ? `/dossiers/${page.ficheId}` : null)
  const onglet: OngletPage = sousFiche.data?.statut === 'clos' && !page.surListe ? 'clos' : page.onglet
  const nAttente = (attente.data?.factures.length ?? 0) + (attente.data?.sans_facture.length ?? 0)
  const a = apercu.data
  return (
    <Page titre={TITRE}>
      <EnTete titre={TITRE} sous={SOUS} actions={<Actions page={page} />} />
      <IndicateursPage apercu={a} />
      <Onglets
        libelle="Dossiers d’importation"
        actif={onglet}
        onChange={page.choisirOnglet}
        onglets={[
          { cle: 'ouverts', libelle: 'Dossiers ouverts', compte: a ? a.ouvert : null },
          { cle: 'clos', libelle: 'Dossiers clos', compte: a ? a.clos : null },
          { cle: 'rattacher', libelle: 'En attente de dossier', compte: attente.data ? nAttente : null },
        ]}
      />
      <Onglet page={page} onglet={onglet} attente={nAttente} clos={clos} />
      {page.nouveau ? <NouveauDossier page={page} clos={clos} /> : null}
      {page.ficheId != null ? <FicheDossier id={page.ficheId} onFermer={page.fermer} /> : null}
    </Page>
  )
}
