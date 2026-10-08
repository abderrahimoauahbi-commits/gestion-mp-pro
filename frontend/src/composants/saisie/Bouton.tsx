/**
 * Le bouton de geste (A8). Il ne se grise **jamais sans dire pourquoi** : la seule façon de le
 * griser est de donner une raison — `manque` (ce qui reste à renseigner), `blocages` (ce que le
 * serveur refusera, calculé par lui) ou `grise` (une autre raison dite) — ou qu'un envoi soit en
 * cours. La raison est l'infobulle et la description accessible au bureau, et s'écrit **sous le
 * bouton** à l'atelier (le doigt n'a pas d'infobulle). Elle est aussi dans `data-raison`, que la
 * recette lit : un bouton grisé sans `data-raison` est une anomalie.
 *
 * Un `onClick` qui rend une promesse occupe le bouton touché, qui affiche son libellé d'attente
 * (« Enregistrement… ») ; un refus du serveur est dit par `Messages`. Le nom accessible est le
 * libellé visible ; `titre` (ce que fait le geste, M72) va en description.
 */
import { useId, useState, type ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import { Icone, type NomIcone } from '../mise-en-page/Icone'
import { direErreur } from '../retour/Messages'
import styles from './Bouton.module.css'

export interface BoutonProps {
  children: ReactNode
  onClick?: () => unknown
  variante?: 'principal' | 'neutre' | 'danger' | 'fantome'
  taille?: 'normal' | 'petit' | 'atelier'
  /** Ce qui reste à renseigner (« la date », « le magasin »). */
  manque?: readonly string[]
  /** Ce que le serveur refusera (ses `blocages`). */
  blocages?: readonly string[]
  /** Une autre raison de griser, dite telle quelle. */
  grise?: string
  /** Un envoi en cours, piloté par l'appelant. */
  occupe?: boolean
  /** Le libellé pendant l'envoi. */
  attente?: string
  /** Ce que fait le geste (infobulle quand il n'est pas grisé). */
  titre?: string
  type?: 'button' | 'submit'
  bloc?: boolean
  icone?: NomIcone
  className?: string
}

const liste = (mots: readonly string[]) => mots.join(', ')

/** La raison d'un bouton grisé, ou '' s'il ne l'est pas. */
export function raisonGrise({
  manque = [],
  blocages = [],
  grise,
}: Pick<BoutonProps, 'manque' | 'blocages' | 'grise'>) {
  const raisons: string[] = []
  if (manque.length) raisons.push(`À renseigner : ${liste(manque)}.`)
  if (blocages.length) raisons.push(`Sera refusé : ${blocages.join(' ; ')}.`.replace(/\.\.$/, '.'))
  if (grise) raisons.push(grise)
  return raisons.join(' ')
}

export function Bouton(props: BoutonProps) {
  const { children, onClick, variante = 'neutre', taille = 'normal', occupe = false, attente } = props
  const id = useId()
  const [envoi, setEnvoi] = useState(false)
  const raison = raisonGrise(props)
  const enCours = occupe || envoi
  const description = raison || (enCours ? 'Envoi en cours.' : props.titre)
  const clic = async () => {
    if (!onClick || enCours || raison) return
    const retour = onClick()
    if (!(retour instanceof Promise)) return
    setEnvoi(true)
    try {
      await retour
    } catch (e) {
      direErreur(e)
    } finally {
      setEnvoi(false)
    }
  }
  const atelier = taille === 'atelier'
  const bouton = (
    <button
      type={props.type ?? 'button'}
      className={classes(
        styles.bouton,
        styles[variante],
        styles[taille],
        props.bloc && styles.bloc,
        props.className,
      )}
      disabled={Boolean(raison) || enCours}
      aria-busy={enCours || undefined}
      aria-describedby={description ? `${id}-raison` : undefined}
      data-raison={raison || (enCours ? 'Envoi en cours.' : undefined)}
      title={atelier ? undefined : description}
      onClick={props.type === 'submit' ? undefined : clic}
    >
      {props.icone ? <Icone nom={props.icone} /> : null}
      {enCours && attente ? attente : children}
    </button>
  )
  if (!description) return bouton
  return (
    <>
      {bouton}
      <span id={`${id}-raison`} className={atelier && raison ? styles.raison : 'masque-accessible'}>
        {description}
      </span>
    </>
  )
}
