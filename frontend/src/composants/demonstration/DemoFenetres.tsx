/** Démonstration des fenêtres : garde de saisie, pile, tiroir, confirmation sur place, lecture longue. */
import { useState } from 'react'

import { Carte } from '../mise-en-page/Carte'
import { Fenetre, useFermerFenetre } from '../mise-en-page/Fenetre'
import { FenetreConfirmation } from '../mise-en-page/FenetreConfirmation'
import { Page } from '../mise-en-page/Page'
import { dire } from '../retour/Messages'
import { Bouton } from '../saisie/Bouton'
import { Champ } from '../saisie/Champ'
import { Confirmer } from '../saisie/Confirmer'
import { Saisie } from '../saisie/Saisie'
import styles from './Demonstration.module.css'

function Annuler() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Annuler</Bouton>
}

function FenetreSaisie({ onFermer }: { onFermer: () => void }) {
  const [texte, setTexte] = useState('')
  const [dessus, setDessus] = useState(false)
  return (
    <Fenetre
      titre="Nouvelle réclamation"
      sous="Tapez quelque chose, puis Échap ou ×"
      onFermer={onFermer}
      sale={texte !== ''}
      taille="large"
      pied={
        <>
          <Annuler />
          <Bouton variante="principal" manque={texte ? [] : ['le motif']} onClick={onFermer}>
            Enregistrer
          </Bouton>
        </>
      }
    >
      <Champ libelle="Motif" obligatoire>
        <Saisie valeur={texte} onChange={setTexte} />
      </Champ>
      <Bouton onClick={() => setDessus(true)}>Ouvrir une fenêtre par-dessus</Bouton>
      {dessus ? (
        <Fenetre titre="Fenêtre du dessus" onFermer={() => setDessus(false)}>
          <p>Échap ne ferme que celle-ci.</p>
        </Fenetre>
      ) : null}
    </Fenetre>
  )
}

function CarteConfirmer() {
  return (
    <Carte titre="Confirmer sur place">
      <div className={styles.rangee}>
        <Confirmer
          question="Retirer ce document ?"
          oui="Oui, retirer"
          variante="danger"
          onOui={() => dire('Document retiré.')}
        >
          Retirer
        </Confirmer>
        <Confirmer
          question="Annuler cette réception ?"
          oui="Oui, annuler"
          motif="exige"
          variante="danger"
          titre="Annule la réception par contre-passation"
          onOui={(m) => dire(`Annulée : ${m}`)}
        >
          Annuler (contre-passation)
        </Confirmer>
        <Confirmer
          question="Valider ?"
          oui="Oui, valider"
          blocages={['un inventaire est ouvert sur ce magasin']}
          onOui={() => {}}
        >
          Valider
        </Confirmer>
      </div>
    </Carte>
  )
}

export function DemoFenetres() {
  const [saisie, setSaisie] = useState(false)
  const [tiroir, setTiroir] = useState(false)
  const [restaurer, setRestaurer] = useState(false)
  return (
    <Page titre="Fenêtres et confirmations">
      <Carte titre="Fenêtres">
        <div className={styles.rangee}>
          <Bouton onClick={() => setSaisie(true)}>Fenêtre de saisie (garde)</Bouton>
          <Bouton onClick={() => setTiroir(true)}>Tiroir</Bouton>
          <Bouton variante="danger" onClick={() => setRestaurer(true)}>
            Restaurer une sauvegarde…
          </Bouton>
        </div>
      </Carte>
      <CarteConfirmer />
      {saisie ? <FenetreSaisie onFermer={() => setSaisie(false)} /> : null}
      {tiroir ? (
        <Fenetre titre="LOT-2026-0042" sous="Fiche en tiroir" tiroir onFermer={() => setTiroir(false)}>
          <p>Le tiroir garde la liste visible à gauche.</p>
        </Fenetre>
      ) : null}
      {restaurer ? (
        <FenetreConfirmation
          titre="Restaurer la sauvegarde du 07/10/2026 03:00"
          texte="Toutes les données saisies depuis seront remplacées. Une sauvegarde « avant restauration » est faite d’abord."
          oui="Restaurer cette sauvegarde"
          variante="danger"
          caseJaiCompris="J’ai compris : les données actuelles seront remplacées."
          onOui={() => dire('Restauration demandée.')}
          onFermer={() => setRestaurer(false)}
        />
      ) : null}
    </Page>
  )
}
