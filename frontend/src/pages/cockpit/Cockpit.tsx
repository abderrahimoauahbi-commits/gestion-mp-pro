/**
 * Le Cockpit de la direction (`/cockpit?onglet=faire|alertes|ensemble|evolution|economies`) : la
 * situation au jour du serveur, recalculée à chaque ouverture depuis les mouvements de stock. Six
 * indicateurs reçus avec leur formule (chacun ouvre son écran), le bilan du mois à imprimer, puis
 * un onglet par question. La fenêtre d'un besoin signalé s'ouvre par l'adresse (`?signalement=ID`).
 */
import { EnTete } from '../../composants/coque/EnTete'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { useOngletAdresse } from '../../lib/adresse'
import { date } from '../../lib/format'
import { useSession } from '../../lib/session'
import { BesoinSignale } from '../accueil/BesoinSignale'
import {
  useBesoins,
  useBrouillons,
  useCockpit,
  useCommandesToutes,
  useInventairesOuverts,
  useReclamationsOuvertes,
  useSauvegardes,
} from '../accueil/donnees'
import { retardsDe } from '../accueil/taches'
import type { Cockpit as DonneesCockpit } from '../accueil/types'
import { aApprouver, actionsCockpit, tacheSauvegarde, totalAFaire } from './aFaire'
import { BilanDuMois } from './BilanDuMois'
import { IndicateursCockpit } from './IndicateursCockpit'
import { OngletAFaire } from './OngletAFaire'
import { OngletAlertes } from './OngletAlertes'
import { OngletEconomies } from './OngletEconomies'
import { OngletEnsemble } from './OngletEnsemble'
import { OngletEvolution } from './OngletEvolution'

type Onglet = 'faire' | 'alertes' | 'ensemble' | 'evolution' | 'economies'
const CLES: readonly Onglet[] = ['faire', 'alertes', 'ensemble', 'evolution', 'economies']

/** Ce qui attend une action : les lectures, la liste, le compte de l'onglet. */
function useAFaire(cockpit: DonneesCockpit | undefined) {
  const { role } = useSession()
  const commandes = useCommandesToutes()
  const brouillons = useBrouillons()
  const inventaires = useInventairesOuverts()
  const besoins = useBesoins()
  const reclamations = useReclamationsOuvertes()
  const sauvegardes = useSauvegardes()
  const lectures = [commandes, brouillons, inventaires, besoins, reclamations]
  const actions = cockpit
    ? actionsCockpit({
        role,
        cockpit,
        commandes: commandes.data ?? [],
        retards: retardsDe(commandes.data ?? []),
        brouillons: brouillons.data,
        inventaires: inventaires.data ?? [],
        besoins: besoins.data?.elements ?? [],
        reclamations: reclamations.data ?? [],
      })
    : []
  const sauvegarde = tacheSauvegarde(role, sauvegardes.data, sauvegardes.error)
  return {
    actions,
    sauvegarde: sauvegarde?.tache ?? null,
    approuver: aApprouver(commandes.data ?? []),
    total: totalAFaire(actions, sauvegarde?.enAlerte ?? false),
    pret: lectures.every((l) => !l.isPending),
    erreurs: lectures.filter((l) => l.isError),
  }
}

type AFaire = ReturnType<typeof useAFaire>

function Contenu({ cockpit, onglet, aFaire }: { cockpit: DonneesCockpit; onglet: Onglet; aFaire: AFaire }) {
  return (
    <>
      {aFaire.erreurs.map((l, i) => (
        <Erreur key={i} erreur={l.error} onReessayer={() => void l.refetch()} />
      ))}
      {onglet === 'faire' ? (
        <OngletAFaire
          cockpit={cockpit}
          approuver={aFaire.approuver}
          actions={aFaire.actions}
          sauvegarde={aFaire.sauvegarde}
          pret={aFaire.pret}
        />
      ) : null}
      {onglet === 'alertes' ? <OngletAlertes cockpit={cockpit} /> : null}
      {onglet === 'ensemble' ? <OngletEnsemble cockpit={cockpit} /> : null}
      {onglet === 'evolution' ? <OngletEvolution /> : null}
      {onglet === 'economies' ? <OngletEconomies cockpit={cockpit} /> : null}
    </>
  )
}

function OngletsCockpit({
  cockpit,
  onglet,
  choisir,
  total,
}: {
  cockpit: DonneesCockpit
  onglet: Onglet
  choisir: (o: Onglet) => void
  total: number
}) {
  return (
    <Onglets<Onglet>
      libelle="Onglets du Cockpit"
      actif={onglet}
      onChange={choisir}
      onglets={[
        { cle: 'faire', libelle: 'À faire et à valider', compte: total || null },
        { cle: 'alertes', libelle: 'Matières en alerte', compte: cockpit.nb_alertes },
        { cle: 'ensemble', libelle: 'Vue d’ensemble' },
        { cle: 'evolution', libelle: 'Évolution' },
        {
          cle: 'economies',
          libelle: 'Opportunités d’économies',
          court: 'Opportunités',
          compte: cockpit.economies.nb_opportunites,
        },
      ]}
    />
  )
}

export default function Cockpit() {
  const cockpit = useCockpit()
  const [onglet, choisir] = useOngletAdresse<Onglet>(CLES, 'faire')
  const c = cockpit.data
  const aFaire = useAFaire(c)
  return (
    <Page titre="Cockpit">
      <EnTete
        titre="Cockpit"
        sous={
          c
            ? `Situation au ${date(c.date_reference)}, recalculée à chaque ouverture depuis les mouvements de stock.`
            : 'Recalculé à chaque ouverture depuis les mouvements de stock.'
        }
        actions={<BilanDuMois />}
      />
      {cockpit.isPending ? <Chargement quoi="le cockpit" /> : null}
      <Erreur erreur={cockpit.error} onReessayer={() => void cockpit.refetch()} />
      {c ? (
        <>
          <IndicateursCockpit kpi={c.kpi} />
          <OngletsCockpit cockpit={c} onglet={onglet} choisir={choisir} total={aFaire.total} />
          <Contenu cockpit={c} onglet={onglet} aFaire={aFaire} />
        </>
      ) : null}
      <BesoinSignale />
    </Page>
  )
}
