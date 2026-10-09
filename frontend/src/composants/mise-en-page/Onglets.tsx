/**
 * Les onglets d'un écran (ECRANS-PRO § 3) : un seul niveau, jamais deux rangées ; libellé court
 * avec le nom complet en infobulle quand la rangée serait trop longue ; compteur quand il a un
 * sens ; « • » sur un onglet dont la saisie n'est pas enregistrée. L'onglet ouvert vit dans
 * l'adresse (`?onglet=`, `useOngletAdresse` de `lib/adresse.ts`) : la page le passe en `actif`.
 *
 * Clavier (motif ARIA des onglets) : ← → passent d'un onglet à l'autre, Début et Fin aux bouts.
 *
 * `garde` : changer d'onglet perd la saisie en cours (l'onglet la tient, la page ne la garde pas) ;
 * tant qu'une saisie est en cours, le changement demande d'abord « Des modifications ne sont pas
 * enregistrées. Les abandonner ? » (`proteger`, la même question que la garde de navigation).
 */
import { useRef, type KeyboardEvent, type ReactNode } from 'react'

import { nombre } from '../../lib/format'
import { proteger } from '../coque/garde'
import { classes } from './classes'
import styles from './Onglets.module.css'

export interface Onglet<T extends string> {
  cle: T
  libelle: string
  /** Libellé affiché quand le complet est trop long (« Opportunités ») ; le complet va en infobulle. */
  court?: string
  compte?: number | null
  /** Une saisie de cet onglet n'est pas enregistrée. */
  sale?: boolean
}

/** L'onglet visé par une touche (← → bouclent, Début, Fin), ou `null`. */
export function ongletVise(touche: string, i: number, bout: number): number | null {
  if (touche === 'ArrowRight') return i === bout ? 0 : i + 1
  if (touche === 'ArrowLeft') return i === 0 ? bout : i - 1
  if (touche === 'Home') return 0
  if (touche === 'End') return bout
  return null
}

function BoutonOnglet<T extends string>({
  onglet: o,
  choisi,
  onClick,
  onKeyDown,
}: {
  onglet: Onglet<T>
  choisi: boolean
  onClick: () => void
  onKeyDown: (e: KeyboardEvent<HTMLButtonElement>) => void
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={choisi}
      tabIndex={choisi ? 0 : -1}
      title={o.court ? o.libelle : undefined}
      aria-label={o.court ? o.libelle : undefined}
      className={classes(styles.onglet, choisi && styles.actif)}
      onClick={onClick}
      onKeyDown={onKeyDown}
    >
      <span>{o.court ?? o.libelle}</span>
      {o.compte != null ? <span className={styles.compte}>{nombre(o.compte)}</span> : null}
      {o.sale ? (
        <span className={styles.sale} title="Saisie non enregistrée">
          •<span className="masque-accessible"> (saisie non enregistrée)</span>
        </span>
      ) : null}
    </button>
  )
}

export function Onglets<T extends string>({
  onglets,
  actif,
  onChange,
  libelle = 'Onglets',
  apres,
  garde = false,
}: {
  onglets: readonly Onglet<T>[]
  actif: T
  onChange: (cle: T) => void
  libelle?: string
  /** Ce qui suit la rangée à droite (une bascule, un bouton). */
  apres?: ReactNode
  /** Changer d'onglet perd la saisie en cours : le demander d'abord. */
  garde?: boolean
}) {
  const rangee = useRef<HTMLDivElement>(null)
  const changer = (cle: T) => {
    if (garde && cle !== actif) proteger(() => onChange(cle))
    else onChange(cle)
  }
  const clavier = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const cible = ongletVise(e.key, i, onglets.length - 1)
    if (cible == null) return
    e.preventDefault()
    const o = onglets[cible]
    if (!o) return
    changer(o.cle)
    rangee.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[cible]?.focus()
  }
  return (
    <div className={styles.barre}>
      <div className={styles.onglets} role="tablist" aria-label={libelle} ref={rangee}>
        {onglets.map((o, i) => {
          const choisi = o.cle === actif
          return (
            <BoutonOnglet
              key={o.cle}
              onglet={o}
              choisi={choisi}
              onClick={() => changer(o.cle)}
              onKeyDown={(e) => clavier(e, i)}
            />
          )
        })}
      </div>
      {apres ? <div className={styles.apres}>{apres}</div> : null}
    </div>
  )
}
