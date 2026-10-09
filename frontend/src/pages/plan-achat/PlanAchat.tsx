/**
 * Plan d'achat (`/plan-achat?onglet=fournisseurs|references`, ECRANS-PRO 4.1–4.4 ; direction,
 * achats) : ce qu'il faut commander, chez qui, et quand. Une recherche partagée par les deux
 * onglets (`?q=`), des filtres liés propres à chacun ; « Préparer la commande » ouvre la
 * préparation en fenêtre à adresse stable (`/plan-achat/preparer/:fournisseurId`).
 */
import { useCallback } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { useOngletAdresse } from '../../lib/adresse'
import { date } from '../../lib/format'
import { useSession } from '../../lib/session'
import { useApresCreation } from './apresCreation'
import { usePlanAchat } from './donnees'
import { IndicateursPlan } from './IndicateursPlan'
import { lienSi } from './liens'
import { OngletFournisseurs } from './OngletFournisseurs'
import { OngletReferences } from './OngletReferences'
import { Preparation } from './Preparation'

const ONGLETS = ['fournisseurs', 'references'] as const
type OngletPlan = (typeof ONGLETS)[number]
const FILTRES: Record<OngletPlan, readonly string[]> = {
  fournisseurs: ['urgence', 'devise', 'pays'],
  references: ['statut', 'priorite', 'abc', 'fournisseur'],
}

/** Fermer la préparation rend le plan avec ses onglet, recherche et filtres ; créer mène aux bons. */
function usePreparationAdresse() {
  const navigate = useNavigate()
  const { search } = useLocation()
  const ouvrir = useCallback(
    (id: number) => navigate(`/plan-achat/preparer/${id}${search}`),
    [navigate, search],
  )
  const fermer = useCallback(() => navigate(`/plan-achat${search}`), [navigate, search])
  return { ouvrir, fermer, cree: useApresCreation() }
}

export default function PlanAchat() {
  const { role } = useSession()
  const plan = usePlanAchat()
  const [onglet, choisir] = useOngletAdresse<OngletPlan>(ONGLETS, 'fournisseurs')
  const etat = useEtatTableAdresse(FILTRES[onglet])
  const prep = usePreparationAdresse()
  const fournisseurId = Number(useParams().fournisseurId) || null
  const besoins = lienSi(role, '/production?onglet=besoins')
  const p = plan.data
  const actions = (
    <>
      {besoins ? (
        <Link to={besoins} title="Les kilos que le plan de production consommera, mois par mois">
          Besoins des mois à venir
        </Link>
      ) : null}
      <ExportExcel route="/export/pilotage" libelle="Classeur de pilotage complet" />
    </>
  )
  return (
    <Page titre="Plan d’achat">
      <EnTete
        titre="Plan d’achat"
        sous={`Ce qu’il faut commander au ${date(p?.date_reference)}, chez qui, et quand. « Préparer la commande » ouvre la proposition à arbitrer.`}
        actions={actions}
      />
      {plan.isError ? <Erreur erreur={plan.error} onReessayer={() => void plan.refetch()} /> : null}
      {plan.isPending ? <Chargement quoi="le plan d’achat" /> : null}
      {p ? <IndicateursPlan plan={p} role={role} /> : null}
      {p ? (
        <Onglets<OngletPlan>
          libelle="Onglets du plan d’achat"
          actif={onglet}
          onChange={choisir}
          onglets={[
            { cle: 'fournisseurs', libelle: 'Par fournisseur', compte: p.fournisseurs.length },
            { cle: 'references', libelle: 'Références à commander', compte: p.lignes.length },
          ]}
        />
      ) : null}
      {p && onglet === 'fournisseurs' ? (
        <OngletFournisseurs fournisseurs={p.fournisseurs} etat={etat} onPreparer={prep.ouvrir} />
      ) : null}
      {p && onglet === 'references' ? (
        <OngletReferences lignes={p.lignes} etat={etat} role={role} onPreparer={prep.ouvrir} />
      ) : null}
      {fournisseurId ? (
        <Preparation fournisseurId={fournisseurId} onFermer={prep.fermer} onCree={prep.cree} />
      ) : null}
    </Page>
  )
}
