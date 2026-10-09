/**
 * Restaurer une sauvegarde (route 45) : après « Oui, continuer… » sur la ligne, une
 * `FenetreConfirmation` en deux étapes — ce qui va disparaître et la case « J'ai compris : la base
 * va revenir en arrière. », puis le mot RESTAURER et le motif (3 caractères au moins). Le serveur répond 202 dès que l'état
 * actuel est sauvegardé ; la fenêtre suit alors `/api/sante` → `taches.restauration`
 * (« en cours », puis « ok » ou « échec : … ») et ne se ferme pas pendant l'opération.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { FenetreConfirmation } from '../../composants/mise-en-page/FenetreConfirmation'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { MOTIF_MIN } from '../../composants/saisie/Confirmer'
import { api } from '../../lib/api'
import { horodatage } from '../../lib/format'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'

export type FichierSauvegarde = Schema<'FichierSauvegarde'>
type Sante = Schema<'Sante'>

export const MOT = 'RESTAURER'
/** Le temps entre deux lectures de la santé pendant la restauration. */
export const PAS_DE_SUIVI = 1500

type Etape = 'confirmation' | 'suivi' | 'faite' | 'echec'

const etatRestauration = async () => (await api.get<Sante>('/sante')).taches?.restauration

/** L'issue de la restauration lue dans la santé : `null` tant qu'elle n'est pas finie. */
export function issue(lu: string | undefined, vuEnCours: boolean, avant: string | undefined, tours: number) {
  if (!lu || lu === 'en cours') return null
  const nouvelle = vuEnCours || lu !== avant || tours >= 10
  if (!nouvelle) return null
  return lu === 'ok' ? 'faite' : 'echec'
}

function useSuivi(
  actif: boolean,
  avant: string | undefined,
  onFin: (e: 'faite' | 'echec', texte: string) => void,
) {
  const rappel = useRef(onFin)
  useEffect(() => {
    rappel.current = onFin
  })
  useEffect(() => {
    if (!actif) return undefined
    let vuEnCours = false
    let tours = 0
    const t = setInterval(() => {
      tours += 1
      etatRestauration()
        .then((lu) => {
          if (lu === 'en cours') vuEnCours = true
          const fin = issue(lu, vuEnCours, avant, tours)
          if (fin) {
            clearInterval(t)
            rappel.current(fin, lu ?? '')
          }
        })
        .catch(() => undefined)
    }, PAS_DE_SUIVI)
    return () => clearInterval(t)
  }, [actif, avant])
}

/** La lecture de la première étape : ce qui va disparaître. */
function Lecture({ f }: { f: FichierSauvegarde }) {
  return (
    <>
      <Note ton="critique">
        Tout ce qui a été saisi depuis le {horodatage(f.quand)} — réceptions, sorties, commandes, réglages —
        disparaîtra de la base, pour tous les postes.
      </Note>
      <ul className={styles.liste}>
        <li>L’état actuel est d’abord sauvegardé (« avant restauration ») : on pourra y revenir.</li>
        <li>Prévenir les autres utilisateurs : ce qu’ils sont en train de saisir sera perdu.</li>
        <li>L’opération peut prendre quelques minutes ; ne pas fermer la fenêtre.</li>
      </ul>
    </>
  )
}

/** Ce que la fenêtre montre une fois la restauration lancée : le suivi, puis l'issue. */
function Issue({ etape, f, texte }: { etape: Etape; f: FichierSauvegarde; texte: string }) {
  if (etape === 'suivi') return <Chargement quoi="la restauration (ne pas fermer la fenêtre)" />
  if (etape === 'faite')
    return (
      <Note ton="ok">
        {`La base est revenue à l’état du ${horodatage(f.quand)}. Les autres postes doivent rouvrir leur écran ; si la session est perdue, se reconnecter.`}
      </Note>
    )
  return <Note ton="critique">{`La restauration a échoué : ${texte.replace(/^échec : /, '')}`}</Note>
}

export function FenetreRestauration({ f, onFermer }: { f: FichierSauvegarde; onFermer: () => void }) {
  const client = useQueryClient()
  const [etape, setEtape] = useState<Etape>('confirmation')
  const [avant, setAvant] = useState<string | undefined>(undefined)
  const [texte, setTexte] = useState('')
  useSuivi(etape === 'suivi', avant, (fin, lu) => {
    setTexte(lu)
    setEtape(fin)
    if (fin === 'faite') void client.invalidateQueries()
  })
  return (
    <FenetreConfirmation
      titre={`Restaurer la sauvegarde du ${horodatage(f.quand)}`}
      etapes={[{ texte: <Lecture f={f} />, caseJaiCompris: 'J’ai compris : la base va revenir en arrière.' }]}
      texte={
        <p>
          Dernière confirmation : taper <strong>{MOT}</strong> pour remplacer la base par la sauvegarde du{' '}
          {horodatage(f.quand)}.
        </p>
      }
      mot={MOT}
      motif="exige"
      motifMin={MOTIF_MIN}
      motifMax={300}
      aideMotif="écrit au journal des actions"
      oui="Restaurer maintenant"
      variante="danger"
      fermerApres={false}
      onOui={async (motif, mot) => {
        const lu = await etatRestauration().catch(() => undefined)
        await api.post(`/sauvegardes/${encodeURIComponent(f.nom)}/restaurer`, {
          confirmation: mot ?? '',
          motif,
        })
        setAvant(lu)
        setEtape('suivi')
      }}
      issue={
        etape === 'confirmation'
          ? null
          : { corps: <Issue etape={etape} f={f} texte={texte} />, fermable: etape !== 'suivi' }
      }
      onFermer={onFermer}
    />
  )
}
