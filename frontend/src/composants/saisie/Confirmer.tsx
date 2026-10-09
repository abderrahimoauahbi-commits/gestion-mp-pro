/**
 * Un geste irréversible confirmé **sur place** (A3, M72) : le bouton devient « question · Non ·
 * Oui, … » là où l'on a cliqué — jamais de boîte du navigateur. La question dit l'effet
 * (« Sortir 445,4 kg de Morocco pour FB + MF, daté d'hier 03/10 ? »). Un motif se saisit dans la
 * confirmation quand il est demandé (`motif`), et « Oui » reste grisé tant qu'un motif exigé
 * manque ou reste plus court que `motifMin` (« un motif de 3 caractères au moins » : le serveur
 * n'a pas à le refuser après coup, A8). Pendant l'envoi, « Oui » est occupé ; un refus du serveur est dit par `Messages` et la
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
  /** La longueur la plus courte d'un motif exigé (celle du serveur) ; 1 par défaut. */
  motifMin?: number
  /** Le nom du champ du motif (« Motif du renvoi aux achats ») ; « Motif (obligatoire) » sinon. */
  libelleMotif?: string
  /** L'exemple écrit dans le champ du motif. */
  exempleMotif?: string
  /** La longueur la plus longue du motif (celle du serveur) ; 500 par défaut. */
  motifMax?: number
  variante?: 'neutre' | 'principal' | 'danger'
  taille?: 'normal' | 'petit' | 'atelier'
  attente?: string
}

/** Le motif le plus court des routes qui en exigent un vrai (`MOTIF_MIN` du serveur : 3). */
export const MOTIF_MIN = 3

/** Ce qui manque au motif exigé : rien, « le motif », ou « un motif de N caractères au moins ». */
export function manqueMotif(texte: string, min = 1): string[] {
  const longueur = texte.trim().length
  if (longueur >= Math.max(1, min)) return []
  return min > 1 ? [`un motif de ${min} caractères au moins`] : ['le motif']
}

/** Le motif saisi dans la confirmation (obligatoire ou facultatif, dit dans son nom). */
function ChampMotif({
  props,
  valeur,
  onChange,
}: {
  props: ConfirmerProps
  valeur: string
  onChange: (v: string) => void
}) {
  const nom = props.libelleMotif ?? (props.motif === 'exige' ? 'Motif (obligatoire)' : 'Motif (facultatif)')
  return (
    <span className={styles.motif}>
      <Saisie
        valeur={valeur}
        onChange={onChange}
        libelle={nom}
        placeholder={props.exempleMotif ?? nom}
        max={props.motifMax ?? 500}
      />
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
      {motif ? <ChampMotif props={props} valeur={texte} onChange={setTexte} /> : null}
      <Bouton taille={taille} onClick={fermer}>
        Non
      </Bouton>
      <Bouton
        taille={taille}
        variante={variante === 'neutre' ? 'principal' : variante}
        manque={motif === 'exige' ? manqueMotif(texte, props.motifMin) : undefined}
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
