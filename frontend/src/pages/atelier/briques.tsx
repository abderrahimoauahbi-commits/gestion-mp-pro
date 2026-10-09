/**
 * Les briques des écrans de l'atelier : la fiche (carte d'un objet, rouge en alerte, verte une
 * fois faite), la ligne « libellé · valeur », la raison écrite sous un bouton grisé, et
 * l'écran d'une lecture (chargement honnête, « Pas de réseau » + « Réessayer », jamais une liste
 * vide à la place d'une coupure, an. 3).
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { classes } from '../../composants/mise-en-page/classes'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import styles from './atelier.module.css'

export function Fiche({
  titre,
  ton,
  children,
  libelle,
}: {
  titre?: ReactNode
  ton?: 'alerte' | 'ok'
  children?: ReactNode
  libelle?: string
}) {
  return (
    <section className={classes(styles.fiche, ton && styles[ton])} aria-label={libelle}>
      {titre ? <h2 className={styles.titreFiche}>{titre}</h2> : null}
      {children}
    </section>
  )
}

export function Ligne({
  libelle,
  children,
  grand,
}: {
  libelle: ReactNode
  children: ReactNode
  grand?: boolean
}) {
  return (
    <div className={styles.ligne}>
      <span>{libelle}</span>
      <span className={classes(styles.valeur, grand && styles.grand)}>{children}</span>
    </div>
  )
}

export function NoteAtelier({ children }: { children: ReactNode }) {
  return <p className={styles.note}>{children}</p>
}

/** Un lien qui a l'air d'un bouton de l'atelier (≥ 44 px). */
export function LienBouton({
  vers,
  children,
  principal,
}: {
  vers: string
  children: ReactNode
  principal?: boolean
}) {
  return (
    <Link to={vers} className={classes(styles.lienBouton, principal && styles.principal)}>
      {children}
    </Link>
  )
}

interface Lecture {
  isPending: boolean
  isError: boolean
  error: unknown
  refetch: () => unknown
}

/**
 * Le corps d'un écran tant que ses lectures ne sont pas toutes là : « Chargement… », ou l'erreur
 * (« Pas de réseau » distinct d'un refus) avec « Réessayer ». `null` quand tout est lu.
 */
export function attente(lectures: readonly Lecture[], quoi: string): ReactNode {
  const enErreur = lectures.find((l) => l.isError)
  if (enErreur)
    return (
      <Erreur
        tactile
        erreur={enErreur.error}
        onReessayer={() => lectures.filter((l) => l.isError).forEach((l) => void l.refetch())}
      />
    )
  if (lectures.some((l) => l.isPending)) return <Chargement quoi={quoi} />
  return null
}

/** Un écran entier qui attend ses lectures (titre et « ‹ » toujours là). */
export function EcranEnAttente({
  titre,
  retour,
  corps,
}: {
  titre: string
  retour?: string | false
  corps: ReactNode
}) {
  return (
    <EcranAtelier titre={titre} retour={retour}>
      {corps}
    </EcranAtelier>
  )
}

/** Revenir en haut de l'écran (changement d'étape d'une saisie). jsdom ne fait pas défiler. */
export function enHaut(): void {
  if (!/jsdom/i.test(navigator.userAgent)) window.scrollTo({ top: 0 })
}
