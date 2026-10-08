/**
 * Un geste irréversible confirmé **sur place** (A3, M72) : le bouton devient « question · Non ·
 * Oui, … » là où l'on a cliqué — jamais de boîte du navigateur. La question dit l'effet
 * (« Sortir 445,4 kg de Morocco pour FB + MF, daté d'hier 03/10 ? »). Un motif se saisit dans la
 * confirmation quand il est demandé (`motif`), et « Oui » reste grisé tant qu'un motif exigé
 * manque. Pendant l'envoi, « Oui » est occupé ; un refus du serveur est dit par `Messages` et la
 * confirmation reste ouverte. Échap revient au bouton (sans fermer la fenêtre autour).
 *
 * Le bouton de départ accepte les raisons de `Bouton` (`manque`, `blocages`, `grise`).
 */
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'

import { classes } from '../mise-en-page/classes'
import { Bouton, type BoutonProps } from './Bouton'
import styles from './Confirmer.module.css'
import { Saisie } from './Saisie'

export interface ConfirmerProps extends Pick<
  BoutonProps,
  'manque' | 'blocages' | 'grise' | 'titre' | 'icone'
> {
  /** Le libellé du bouton de départ. */
  children: ReactNode
  question: ReactNode
  /** Le libellé du « Oui » (« Oui, annuler »). */
  oui: string
  onOui: (motif: string) => unknown
  motif?: 'facultatif' | 'exige'
  variante?: 'neutre' | 'principal' | 'danger'
  taille?: 'normal' | 'petit' | 'atelier'
  attente?: string
}

/** Le motif saisi dans la confirmation (obligatoire ou facultatif, dit dans son nom). */
function ChampMotif({
  motif,
  valeur,
  onChange,
}: {
  motif: 'facultatif' | 'exige'
  valeur: string
  onChange: (v: string) => void
}) {
  const nom = motif === 'exige' ? 'Motif (obligatoire)' : 'Motif (facultatif)'
  return (
    <span className={styles.motif}>
      <Saisie valeur={valeur} onChange={onChange} libelle={nom} placeholder={nom} max={500} />
    </span>
  )
}

/** Ce que le bouton de départ reprend de la confirmation (ses raisons de griser, son titre). */
const depart = ({ manque, blocages, grise, titre, icone }: ConfirmerProps) => ({
  manque,
  blocages,
  grise,
  titre,
  icone,
})

/** Échap revient au bouton, sans fermer la fenêtre autour. */
function echapper(e: KeyboardEvent, fermer: () => void) {
  if (e.key !== 'Escape') return
  e.stopPropagation()
  e.nativeEvent.stopImmediatePropagation()
  fermer()
}

export function Confirmer(props: ConfirmerProps) {
  const { children, question, oui, onOui, motif, variante = 'neutre', taille = 'normal', attente } = props
  const [ouvert, setOuvert] = useState(false)
  const [texte, setTexte] = useState('')
  const non = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    if (ouvert) non.current?.querySelector<HTMLElement>(motif ? 'input' : 'button')?.focus()
  }, [ouvert, motif])
  if (!ouvert) {
    return (
      <Bouton {...depart(props)} variante={variante} taille={taille} onClick={() => setOuvert(true)}>
        {children}
      </Bouton>
    )
  }
  const fermer = () => {
    setOuvert(false)
    setTexte('')
  }
  return (
    <span
      ref={non}
      role="group"
      aria-label="Confirmation"
      className={classes(styles.confirmer, taille === 'atelier' && styles.atelier)}
      onKeyDown={(e) => echapper(e, fermer)}
    >
      <span className={styles.question}>{question}</span>
      {motif ? <ChampMotif motif={motif} valeur={texte} onChange={setTexte} /> : null}
      <Bouton taille={taille} onClick={fermer}>
        Non
      </Bouton>
      <Bouton
        taille={taille}
        variante={variante === 'neutre' ? 'principal' : variante}
        manque={motif === 'exige' && !texte.trim() ? ['le motif'] : undefined}
        attente={attente ?? 'Envoi…'}
        onClick={async () => {
          await onOui(texte.trim())
          fermer()
        }}
      >
        {oui}
      </Bouton>
    </span>
  )
}
