/** Les appareils enrôlés (GET /appareils, route 19 : direction et administrateur), en lecture ; on les gère dans Administration › Appareils. */
import { Link } from 'react-router'

import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { date } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { AppareilFiche } from '../../lib/types-coque'
import styles from './MonCompte.module.css'

export function Appareils() {
  const lecture = useLecture<AppareilFiche[]>('/appareils')
  const actifs = (lecture.data ?? []).filter((a) => a.actif && a.enrole)
  return (
    <section className={styles.appareils} aria-label="Appareils enrôlés">
      <h3>Appareils enrôlés</h3>
      {lecture.isPending ? <Chargement quoi="les appareils" /> : null}
      <Erreur erreur={lecture.error} onReessayer={() => void lecture.refetch()} />
      {lecture.data && !actifs.length ? <p className={styles.discret}>Aucun appareil enrôlé.</p> : null}
      <ul>
        {actifs.map((a) => (
          <li key={a.id}>
            <strong>{a.nom}</strong> <span className={styles.discret}>enrôlé le {date(a.enrole_le)}</span>
          </li>
        ))}
      </ul>
      <Link to="/administration?onglet=appareils">Gérer les appareils (Administration › Appareils)</Link>
    </section>
  )
}
