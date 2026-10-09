/**
 * Ma journée des achats (`/accueil`) : quatre indicateurs, puis « À faire » (l'ordre exact de
 * ECRANS-PRO partie 1), « À valider » et « Arrivées attendues dans les 7 jours ». Les comptes
 * viennent du serveur ; l'écran ne fait que compter les listes reçues.
 */
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { Cadre } from '../../composants/tableaux/Cadre'
import { formule } from '../../lib/aide'
import { nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import styles from './accueil.module.css'
import { CarteArrivees, CarteAValider, EtatLectures } from './CartesJournee'
import {
  useAttente,
  useBesoins,
  useBrouillons,
  useCockpit,
  useCommandesToutes,
  useInventairesOuverts,
  useReclamationsOuvertes,
} from './donnees'
import { ListeTaches } from './ListeTaches'
import { arriveesSemaine, retardsDe, siPermis, tachesAchats } from './taches'
import type { Cockpit } from './types'

function IndicateursJournee({
  cockpit,
  retards,
  arrivees,
}: {
  cockpit?: Cockpit
  retards?: number
  arrivees: number
}) {
  const { role } = useSession()
  const rouges = cockpit?.alerte_rouge
  const urgentes = cockpit?.stock.urgents ?? 0
  const c = cockpit?.controles
  const lien = (a: string) => siPermis(role, a) ?? undefined
  return (
    <Indicateurs libelle="Indicateurs de la journée">
      <Kpi
        titre="En rupture ou critiques"
        valeur={rouges == null ? '…' : nombre(rouges)}
        formule={formule('alerte')}
        ton={rouges ? 'critique' : urgentes ? 'urgent' : 'ok'}
        detail={`et ${nombre(urgentes)} urgente(s) · au plan d’achat`}
        lien={lien('/plan-achat')}
      />
      <Kpi
        titre="Arrivées dans les 7 jours"
        valeur={nombre(arrivees)}
        formule={formule('arrivees_semaine')}
        detail="ETA, sinon livraison prévue"
      />
      <Kpi
        titre="Commandes en retard"
        valeur={retards == null ? '…' : nombre(retards)}
        formule={formule('commandes_en_retard')}
        ton={retards ? 'urgent' : 'ok'}
        detail="relancer, noter l’ETA"
        lien={lien('/commandes?filtre=retard')}
      />
      <Kpi
        titre="Contrôles à corriger"
        valeur={c ? nombre(c.a_corriger) : '…'}
        formule={formule('controles_a_corriger')}
        ton={c?.bloquants ? 'critique' : c?.a_corriger ? 'attention' : 'ok'}
        detail={c?.bloquants ? `dont ${nombre(c.bloquants)} bloquant(s)` : 'voir les contrôles'}
        lien={lien('/analyse?onglet=controles')}
      />
    </Indicateurs>
  )
}

export function JourneeAchats() {
  const { role } = useSession()
  const cockpit = useCockpit()
  const commandes = useCommandesToutes()
  const brouillons = useBrouillons()
  const attente = useAttente()
  const besoins = useBesoins()
  const reclamations = useReclamationsOuvertes()
  const inventaires = useInventairesOuverts()
  const taches = tachesAchats({
    role,
    cockpit: cockpit.data,
    commandes: commandes.data ?? [],
    retards: retardsDe(commandes.data ?? []),
    attente: attente.data,
    besoins: besoins.data?.elements ?? [],
    reclamations: reclamations.data ?? [],
    inventaires: inventaires.data ?? [],
  })
  const arrivees = arriveesSemaine(commandes.data ?? [])
  const lectures = [
    [cockpit, 'le cockpit'],
    [commandes, 'les commandes'],
    [attente, 'les factures en attente de dossier'],
    [besoins, 'les besoins signalés'],
    [reclamations, 'les réclamations'],
    [inventaires, 'les inventaires'],
  ] as const
  const pret = lectures.every(([l]) => !l.isPending)
  return (
    <>
      <IndicateursJournee
        cockpit={cockpit.data}
        retards={commandes.data ? retardsDe(commandes.data).length : undefined}
        arrivees={arrivees.length}
      />
      <div className={styles.grille}>
        <Carte titre={`À faire (${nombre(taches.length)})`}>
          <EtatLectures lectures={lectures} />
          <Cadre>
            {pret ? (
              <ListeTaches taches={taches} libelle="À faire" vide="Rien n’attend : tout est à jour." />
            ) : null}
          </Cadre>
        </Carte>
        <CarteAValider brouillons={brouillons} />
        <CarteArrivees arrivees={arrivees} commandes={commandes} />
      </div>
    </>
  )
}
