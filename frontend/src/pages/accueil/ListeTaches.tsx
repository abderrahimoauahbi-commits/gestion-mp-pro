/**
 * Une liste de tâches (Ma journée, Cockpit) : une ligne par tâche, son titre est le lien vers le
 * document ou la liste filtrée ; un besoin signalé porte « Traiter » (sa fenêtre, à adresse
 * stable). Le filet de gauche dit le ton, le badge le redit en mots (la couleur ne parle jamais
 * seule).
 */
import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router'

import { classes } from '../../composants/mise-en-page/classes'
import { Badge } from '../../composants/retour/Badge'
import { avecParametre } from '../../lib/adresse'
import styles from './accueil.module.css'
import type { Tache } from './taches'

/** L'adresse de la page courante avec la fenêtre d'un besoin ouverte (`?signalement=ID`). */
export function useVersBesoin(): (id: number) => string {
  const { pathname, search } = useLocation()
  return (id) => {
    const p = avecParametre(new URLSearchParams(search), 'signalement', String(id))
    return `${pathname}?${p.toString()}`
  }
}

function Titre({ t }: { t: Tache }) {
  const texte = (
    <>
      {t.titre}
      {t.besoin?.urgence === 'urgente' ? (
        <>
          {' '}
          <Badge ton="critique">urgent</Badge>
        </>
      ) : null}
    </>
  )
  return t.vers && !t.lien ? (
    <Link to={t.vers} className={styles.titreTache}>
      {texte}
    </Link>
  ) : (
    <strong className={styles.titreTache}>{texte}</strong>
  )
}

export function LigneTache({ t, action }: { t: Tache; action?: ReactNode }) {
  const versBesoin = useVersBesoin()
  return (
    <li className={classes(styles.tache, t.ton && styles[t.ton])} data-tache={t.cle}>
      {t.compte != null ? <span className={styles.compte}>{t.compte}</span> : null}
      <div className={styles.corpsTache}>
        <Titre t={t} />
        {t.detail ? <span className={styles.detailTache}>{t.detail}</span> : null}
      </div>
      {t.besoin ? (
        <Link
          to={versBesoin(t.besoin.id)}
          className={styles.traiter}
          title="Répondre à l’atelier et ranger ce besoin parmi les traités"
        >
          Traiter
        </Link>
      ) : null}
      {t.vers && t.lien ? (
        <Link to={t.vers} className={styles.lienTache}>
          {t.lien} →
        </Link>
      ) : null}
      {action}
    </li>
  )
}

export function ListeTaches({
  taches,
  vide,
  libelle,
  apres,
}: {
  taches: readonly Tache[]
  vide: string
  libelle: string
  apres?: ReactNode
}) {
  return (
    <ul className={styles.taches} aria-label={libelle}>
      {taches.map((t) => (
        <LigneTache key={t.cle} t={t} />
      ))}
      {apres}
      {!taches.length ? <li className={styles.vide}>{vide}</li> : null}
    </ul>
  )
}
