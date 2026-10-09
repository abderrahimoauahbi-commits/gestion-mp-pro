/**
 * Un geste confirmé sur place avec un motif d'au moins trois caractères (renvoi aux achats,
 * annulation d'une réception) : « Oui » reste grisé, avec sa raison, tant que le motif est trop
 * court — le serveur n'a pas à le refuser après coup (A8). Le reste suit `Confirmer` (E1).
 */
import { useState, type ReactNode } from 'react'

import { Bouton, type BoutonProps } from '../../composants/saisie/Bouton'
import { Saisie } from '../../composants/saisie/Saisie'
import styles from '../plan-achat/achats.module.css'

export const MOTIF_MIN = 3

/** Ce qui manque au motif, ou rien. */
export function manqueMotif(motif: string, min = MOTIF_MIN): string[] {
  return motif.trim().length < min ? [`un motif de ${min} caractères au moins`] : []
}

export function ConfirmerMotif(
  props: Pick<BoutonProps, 'blocages' | 'grise' | 'titre' | 'manque'> & {
    children: ReactNode
    question: ReactNode
    libelleMotif: string
    placeholder?: string
    oui: string
    max: number
    variante?: 'neutre' | 'danger'
    onOui: (motif: string) => Promise<unknown>
  },
) {
  const [ouvert, setOuvert] = useState(false)
  const [motif, setMotif] = useState('')
  const { children, question, oui, onOui, variante = 'danger' } = props
  if (!ouvert)
    return (
      <Bouton
        variante={variante}
        blocages={props.blocages}
        grise={props.grise}
        manque={props.manque}
        titre={props.titre}
        onClick={() => setOuvert(true)}
      >
        {children}
      </Bouton>
    )
  const fermer = () => {
    setOuvert(false)
    setMotif('')
  }
  return (
    <span role="group" aria-label="Confirmation" className={styles.panneau}>
      <span>{question}</span>
      <Saisie
        valeur={motif}
        onChange={setMotif}
        libelle={props.libelleMotif}
        placeholder={props.placeholder}
        max={props.max}
        autoFocus
      />
      <span className={styles.rangeeCentree}>
        <Bouton onClick={fermer}>Non</Bouton>
        <Bouton
          variante={variante === 'neutre' ? 'principal' : variante}
          manque={manqueMotif(motif)}
          attente="Envoi…"
          onClick={async () => {
            await onOui(motif.trim())
            fermer()
          }}
        >
          {oui}
        </Bouton>
      </span>
    </span>
  )
}
