/**
 * La cloche (A10, tous les rôles) : les notifications du compte (GET /notifications, route 53),
 * relues chaque minute ; le nombre de non lues sur la cloche ; « Tout marquer comme lu » (route 55) ;
 * une notification se marque lue (route 54) et ouvre son document par son adresse stable — jamais
 * un écran que le rôle ne voit pas.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'

import { api } from '../../lib/api'
import { permis } from '../../lib/droits'
import { horodatageRelatif, nombre } from '../../lib/format'
import { useEcriture, useLecture } from '../../lib/requetes'
import type { Notification, PageNotifications } from '../../lib/types-coque'
import type { Role } from '../../lib/types'
import { classes } from '../mise-en-page/classes'
import { Icone, type NomIcone } from '../mise-en-page/Icone'
import { Erreur } from '../retour/Erreur'
import { direErreur } from '../retour/Messages'
import styles from './Cloche.module.css'
import { proteger } from './garde'

/** Le nombre de notifications lues à la fois dans le panneau. */
export const NOTIFICATIONS_LUES = 30

const ICONES: Readonly<Record<string, NomIcone>> = {
  info: 'info',
  succes: 'coche',
  alerte: 'attention',
  danger: 'attention',
}

/** Ferme un panneau au clic dehors et à Échap. */
export function useFermeDehors(ouvert: boolean, fermer: () => void) {
  const boite = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ouvert) return
    const clic = (e: MouseEvent) => {
      if (boite.current && e.target instanceof Node && !boite.current.contains(e.target)) fermer()
    }
    const touche = (e: KeyboardEvent) => e.key === 'Escape' && fermer()
    document.addEventListener('mousedown', clic)
    document.addEventListener('keydown', touche)
    return () => {
      document.removeEventListener('mousedown', clic)
      document.removeEventListener('keydown', touche)
    }
  }, [ouvert, fermer])
  return boite
}

function Ligne({ n, role, onOuvrir }: { n: Notification; role: Role; onOuvrir: (n: Notification) => void }) {
  const lien = n.lien && permis(role, n.lien) ? n.lien : null
  return (
    <li>
      <button
        type="button"
        className={classes(styles.ligne, !n.lue && styles.nonLue, styles[n.ton])}
        onClick={() => onOuvrir(n)}
        title={lien ? 'Ouvrir le document' : undefined}
      >
        <Icone nom={ICONES[n.ton] ?? 'info'} />
        <span className={styles.texte}>
          {n.texte}
          <span className={styles.quand}>{horodatageRelatif(n.quand)}</span>
        </span>
        {!n.lue ? <span className="masque-accessible">(non lue)</span> : null}
      </button>
    </li>
  )
}

interface PanneauProps {
  page: PageNotifications | undefined
  erreur: unknown
  role: Role
  onReessayer: () => void
  onToutLu: () => void
  onOuvrir: (n: Notification) => void
}

function Panneau({ page, erreur, role, onReessayer, onToutLu, onOuvrir }: PanneauProps) {
  return (
    <div className={styles.panneau} role="dialog" aria-label="Notifications">
      <div className={styles.tete}>
        <strong>Notifications</strong>
        {page?.non_lues ? (
          <button type="button" className={styles.toutLu} onClick={onToutLu}>
            Tout marquer comme lu
          </button>
        ) : null}
      </div>
      <Erreur erreur={erreur} onReessayer={onReessayer} />
      {page && !page.elements.length ? <p className={styles.vide}>Aucune notification.</p> : null}
      <ul className={styles.liste}>
        {(page?.elements ?? []).map((n) => (
          <Ligne key={n.id} n={n} role={role} onOuvrir={onOuvrir} />
        ))}
      </ul>
    </div>
  )
}

export function Cloche({ role }: { role: Role }) {
  const [ouvert, setOuvert] = useState(false)
  const naviguer = useNavigate()
  const boite = useFermeDehors(ouvert, () => setOuvert(false))
  const lecture = useLecture<PageNotifications>(
    '/notifications',
    { limite: NOTIFICATIONS_LUES },
    { refetchInterval: 60_000 },
  )
  const toutLu = useEcriture(() => api.post<void>('/notifications/lues'))
  const nonLues = lecture.data?.non_lues ?? 0
  const ouvrir = (n: Notification) => {
    setOuvert(false)
    if (!n.lue) api.post<void>(`/notifications/${n.id}/lue`).then(() => lecture.refetch(), direErreur)
    if (n.lien && permis(role, n.lien)) {
      const lien = n.lien
      proteger(() => naviguer(lien))
    }
  }
  const titre = nonLues ? `Notifications : ${nombre(nonLues)} non lue(s)` : 'Notifications'
  return (
    <div className={styles.cloche} ref={boite}>
      <button
        type="button"
        className={styles.bouton}
        aria-label={titre}
        title={titre}
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        <Icone nom="cloche" taille={20} />
        {nonLues ? <span className={styles.compte}>{nonLues > 99 ? '99+' : nonLues}</span> : null}
      </button>
      {ouvert ? (
        <Panneau
          page={lecture.data}
          erreur={lecture.error}
          role={role}
          onReessayer={() => void lecture.refetch()}
          onToutLu={() => toutLu.mutate(undefined, { onError: direErreur })}
          onOuvrir={ouvrir}
        />
      ) : null}
    </div>
  )
}
