/**
 * Les cartes de Ma journée : « À valider » (achats et alimentation), « Arrivées attendues dans les
 * 7 jours » (achats). Chaque carte fait défiler sa liste dans son cadre ; la page ne défile pas.
 */
import type { UseQueryResult } from '@tanstack/react-query'
import { Link } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Cadre } from '../../composants/tableaux/Cadre'
import type { ErreurApi } from '../../lib/api'
import { date, nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import { ListeTaches } from './ListeTaches'
import { arriveeDe, brouillonsVisibles, siPermis, tachesAValider, type Tache } from './taches'
import type { Brouillons, CommandeResume } from './types'

/** Les lectures en cours ou en échec d'une carte : « Chargement… » honnête, « Réessayer ». */
export function EtatLectures({
  lectures,
}: {
  lectures: readonly (readonly [UseQueryResult<unknown, ErreurApi>, string])[]
}) {
  const enCours = lectures.find(([l]) => l.isPending && l.fetchStatus !== 'idle')
  return (
    <>
      {lectures.map(([l, quoi]) =>
        l.isError ? <Erreur key={quoi} erreur={l.error} onReessayer={() => void l.refetch()} /> : null,
      )}
      {enCours ? <Chargement quoi={enCours[1]} /> : null}
    </>
  )
}

export function CarteAValider({ brouillons }: { brouillons: UseQueryResult<Brouillons, ErreurApi> }) {
  const { role } = useSession()
  const taches = tachesAValider(role, brouillonsVisibles(role, brouillons.data))
  const tout = siPermis(role, '/stock?onglet=a-valider')
  const n = brouillonsVisibles(role, brouillons.data).length
  return (
    <Carte
      titre={`À valider (${nombre(n)})`}
      actions={tout && n ? <Link to={tout}>Tout valider…</Link> : null}
    >
      <EtatLectures lectures={[[brouillons, 'les brouillons']]} />
      <Cadre>
        {brouillons.data ? (
          <ListeTaches
            taches={taches}
            libelle="À valider"
            vide="Aucun brouillon : tout ce qui a été saisi est validé."
          />
        ) : null}
      </Cadre>
    </Carte>
  )
}

export function CarteArrivees({
  arrivees,
  commandes,
}: {
  arrivees: readonly CommandeResume[]
  commandes: UseQueryResult<CommandeResume[], ErreurApi>
}) {
  const { role } = useSession()
  const taches: Tache[] = arrivees.map((c) => ({
    cle: `arrivee-${c.id}`,
    titre: `${c.numero ?? 'Brouillon'} · ${c.fournisseur}`,
    detail: `prévue le ${date(arriveeDe(c))} · ${c.livraison_libelle}`,
    vers: siPermis(role, `/commandes/${c.id}`),
  }))
  return (
    <Carte titre={`Arrivées attendues dans les 7 jours (${nombre(arrivees.length)})`}>
      <EtatLectures lectures={[[commandes, 'les commandes']]} />
      <Cadre>
        {commandes.data ? (
          <ListeTaches
            taches={taches}
            libelle="Arrivées attendues"
            vide="Aucune arrivée annoncée cette semaine."
          />
        ) : null}
      </Cadre>
    </Carte>
  )
}
