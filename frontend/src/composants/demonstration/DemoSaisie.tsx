/** Démonstration de la saisie : champs alignés, nombres, quantités, prix, dates, sélecteurs, boutons qui disent pourquoi. */
import { useState } from 'react'

import { aujourdhui } from '../../lib/heure'
import type { Unite } from '../../lib/unites'
import { Carte } from '../mise-en-page/Carte'
import { Grille } from '../mise-en-page/Grille'
import { Page } from '../mise-en-page/Page'
import { Blocages } from '../saisie/Blocages'
import { Bouton } from '../saisie/Bouton'
import { Champ } from '../saisie/Champ'
import { DateChamp } from '../saisie/DateChamp'
import { Interrupteur } from '../saisie/Interrupteur'
import { Nombre } from '../saisie/Nombre'
import { Prix } from '../saisie/Prix'
import { Puces } from '../saisie/Puces'
import { Quantite } from '../saisie/Quantite'
import { Saisie } from '../saisie/Saisie'
import { Segments } from '../saisie/Segments'
import { SelecteurLot } from '../saisie/SelecteurLot'
import { SelecteurMatiere } from '../saisie/SelecteurMatiere'
import { Zone } from '../saisie/Zone'
import styles from './Demonstration.module.css'
import { MATIERES_CHOIX } from './donnees'

function Gestes({ bl, jour }: { bl: string; jour: string }) {
  const [catalogue, setCatalogue] = useState(false)
  return (
    <>
      <Interrupteur
        valeur={catalogue}
        onChange={setCatalogue}
        libelle="Envoyer avec nos prix du catalogue, à confirmer"
      />
      <div className={styles.rangee}>
        <Bouton
          variante="principal"
          manque={[!bl && 'le n° de BL', !jour && 'la date'].filter((x): x is string => Boolean(x))}
          titre="Enregistre le brouillon de réception"
        >
          Enregistrer le brouillon
        </Bouton>
        <Bouton blocages={['un inventaire est ouvert sur le magasin Principal']}>Valider la réception</Bouton>
        <Bouton attente="Enregistrement…" onClick={() => new Promise((ok) => setTimeout(ok, 1500))}>
          Geste qui attend le serveur
        </Bouton>
      </div>
      <Blocages
        blocages={[
          'Date antérieure au dernier ordre validé (07/10/2026).',
          'Le lot LOT-2026-0044 est en quarantaine.',
        ]}
      />
    </>
  )
}

function Formulaire() {
  const [bl, setBl] = useState('')
  const [jour, setJour] = useState(aujourdhui())
  const [seuil, setSeuil] = useState<number | null>(12.5)
  const [prix, setPrix] = useState<number | null>(0.5)
  const [obs, setObs] = useState('')
  const [sens, setSens] = useState<'entree' | 'sortie'>('entree')
  const [couleur, setCouleur] = useState('')
  return (
    <Carte titre="Champs alignés (Grille de 3)">
      <Grille colonnes={3}>
        <Champ libelle="N° de BL" obligatoire aide="Tel qu’écrit sur le bon de livraison.">
          <Saisie valeur={bl} onChange={setBl} />
        </Champ>
        <Champ libelle="Reçu le" obligatoire>
          <DateChamp valeur={jour} onChange={setJour} />
        </Champ>
        <Champ libelle="Seuil d’alerte (jours de couverture)" aide="Entre 1 et 60.">
          <Nombre valeur={seuil} onChange={setSeuil} min={1} max={60} decimales={1} unite="j" />
        </Champ>
        <Champ libelle="Prix au mètre">
          <Prix valeur={prix} onChange={setPrix} devise="USD" unite="ml" densite={0.014} />
        </Champ>
        <Champ libelle="Sens" groupe>
          <Segments
            valeur={sens}
            onChange={setSens}
            options={[
              { valeur: 'entree', libelle: 'Entrée' },
              { valeur: 'sortie', libelle: 'Sortie' },
            ]}
          />
        </Champ>
        <Champ libelle="Couleur" groupe>
          <Puces
            valeur={couleur}
            onChange={setCouleur}
            options={['Rouge', 'Beige', 'Bleu marine', 'Vison', 'Écru', 'Noir']}
            max={4}
            libre
          />
        </Champ>
        <Champ libelle="Observations" large>
          <Zone valeur={obs} onChange={setObs} max={300} />
        </Champ>
      </Grille>
      <Gestes bl={bl} jour={jour} />
    </Carte>
  )
}

function Choix() {
  const [kg, setKg] = useState<number | null>(7.5)
  const [unite, setUnite] = useState<Unite>('kg')
  const [matiere, setMatiere] = useState<number | null>(null)
  const [lot, setLot] = useState<number | null>(null)
  return (
    <Carte titre="Quantités et sélecteurs">
      <Champ libelle="Quantité" groupe aide="Changer d’unité dit l’arrondi.">
        <Quantite
          libelle="Quantité"
          kg={kg}
          onChange={setKg}
          unite={unite}
          onUnite={setUnite}
          poidsBobine={2.4952}
          bobinesPalette={40}
          borne={581.65}
        />
      </Champ>
      <Champ libelle="Matière" groupe>
        <SelecteurMatiere matieres={MATIERES_CHOIX} valeur={matiere} onChange={setMatiere} />
      </Champ>
      <Champ libelle="Lot (présent à la date, FIFO)" groupe>
        <SelecteurLot matiere={matiere} date={aujourdhui()} magasin={1} valeur={lot} onChange={setLot} />
      </Champ>
    </Carte>
  )
}

export function DemoSaisie() {
  return (
    <Page titre="Saisie">
      <div className={styles.colonnes}>
        <Formulaire />
        <Choix />
      </div>
    </Page>
  )
}
