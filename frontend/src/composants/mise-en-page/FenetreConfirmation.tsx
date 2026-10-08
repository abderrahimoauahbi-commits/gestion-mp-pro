/**
 * La confirmation qui demande une **lecture longue** (A3) : restauration d'une sauvegarde,
 * clôture d'un dossier avec ses alertes, clôture de période. Tout autre geste se confirme sur la
 * ligne (`Confirmer`). Le motif s'y saisit quand il est demandé ; `caseJaiCompris` exige de cocher
 * « J'ai compris » avant que le bouton s'active (restauration). Le bouton grisé dit pourquoi ;
 * pendant l'envoi il est occupé ; un refus est dit, la fenêtre reste ouverte ; réussi, elle se ferme.
 */
import { useState, type ReactNode } from 'react'

import { Bouton } from '../saisie/Bouton'
import { Champ } from '../saisie/Champ'
import { Zone } from '../saisie/Zone'
import { Fenetre, useFermerFenetre } from './Fenetre'
import styles from './FenetreConfirmation.module.css'

export interface FenetreConfirmationProps {
  titre: string
  texte: ReactNode
  /** Le libellé du bouton qui confirme (« Restaurer cette sauvegarde »). */
  oui: string
  onOui: (motif: string) => unknown
  onFermer: () => void
  motif?: 'facultatif' | 'exige'
  /** Le texte de la case à cocher (« J'ai compris : les données actuelles seront remplacées. »). */
  caseJaiCompris?: string
  variante?: 'principal' | 'danger'
}

function Annuler() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Annuler</Bouton>
}

export function FenetreConfirmation(props: FenetreConfirmationProps) {
  const { titre, texte, oui, onOui, onFermer, motif, caseJaiCompris, variante = 'principal' } = props
  const [texteMotif, setTexteMotif] = useState('')
  const [compris, setCompris] = useState(false)
  const manque = motif === 'exige' && !texteMotif.trim() ? ['le motif'] : []
  const grise = caseJaiCompris && !compris ? 'Cochez « J’ai compris » pour continuer.' : undefined
  return (
    <Fenetre
      titre={titre}
      onFermer={onFermer}
      sale={Boolean(texteMotif.trim())}
      pied={
        <>
          <Annuler />
          <Bouton
            variante={variante}
            manque={manque}
            grise={grise}
            attente="Envoi…"
            onClick={async () => {
              await onOui(texteMotif.trim())
              onFermer()
            }}
          >
            {oui}
          </Bouton>
        </>
      }
    >
      <div className={styles.texte}>{texte}</div>
      {motif ? (
        <Champ libelle={motif === 'exige' ? 'Motif' : 'Motif (facultatif)'} obligatoire={motif === 'exige'}>
          <Zone valeur={texteMotif} onChange={setTexteMotif} max={500} />
        </Champ>
      ) : null}
      {caseJaiCompris ? (
        <label className={styles.compris}>
          <input type="checkbox" checked={compris} onChange={(e) => setCompris(e.target.checked)} />
          <span>{caseJaiCompris}</span>
        </label>
      ) : null}
    </Fenetre>
  )
}
