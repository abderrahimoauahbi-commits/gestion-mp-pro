/**
 * Restaurer une sauvegarde (route 45) : après « Oui, continuer… » sur la ligne, une fenêtre de
 * lecture longue en deux temps — ce qui va disparaître et la case « J'ai compris : la base va
 * revenir en arrière. », puis le mot RESTAURER et le motif. Le serveur répond 202 dès que l'état
 * actuel est sauvegardé ; la fenêtre suit alors `/api/sante` → `taches.restauration`
 * (« en cours », puis « ok » ou « échec : … ») et ne se ferme pas pendant l'opération.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api } from '../../lib/api'
import { horodatage } from '../../lib/format'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'

export type FichierSauvegarde = Schema<'FichierSauvegarde'>
type Sante = Schema<'Sante'>

export const MOT = 'RESTAURER'
/** Le temps entre deux lectures de la santé pendant la restauration. */
export const PAS_DE_SUIVI = 1500

type Etape = 'lecture' | 'mot' | 'suivi' | 'faite' | 'echec'

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

function Lecture({
  f,
  onSuite,
  onFermer,
}: {
  f: FichierSauvegarde
  onSuite: () => void
  onFermer: () => void
}) {
  const [compris, setCompris] = useState(false)
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
      <label className={styles.case}>
        <input type="checkbox" checked={compris} onChange={(e) => setCompris(e.target.checked)} />
        J’ai compris : la base va revenir en arrière.
      </label>
      <div className={styles.rangee}>
        <span className={styles.pousse} />
        <Bouton onClick={onFermer}>Annuler</Bouton>
        <Bouton
          variante="danger"
          grise={compris ? undefined : 'Cocher « J’ai compris » d’abord.'}
          onClick={onSuite}
        >
          Continuer
        </Bouton>
      </div>
    </>
  )
}

function Mot({
  f,
  onLancee,
  onFermer,
}: {
  f: FichierSauvegarde
  onLancee: (avant: string | undefined) => void
  onFermer: () => void
}) {
  const [mot, setMot] = useState('')
  const [motif, setMotif] = useState('')
  const manque = [
    ...(mot.trim().toUpperCase() === MOT ? [] : [`le mot ${MOT}`]),
    ...(motif.trim().length >= 3 ? [] : ['le motif (3 caractères au moins)']),
  ]
  return (
    <>
      <p>
        Dernière confirmation : taper <strong>{MOT}</strong> pour remplacer la base par la sauvegarde du{' '}
        {horodatage(f.quand)}.
      </p>
      <Champ libelle={`Taper ${MOT}`} obligatoire>
        <Saisie valeur={mot} max={20} onChange={setMot} autoFocus />
      </Champ>
      <Champ libelle="Motif" aide="écrit au journal des actions" obligatoire>
        <Saisie valeur={motif} max={300} onChange={setMotif} />
      </Champ>
      <div className={styles.rangee}>
        <span className={styles.pousse} />
        <Bouton onClick={onFermer}>Annuler</Bouton>
        <Bouton
          variante="danger"
          manque={manque}
          attente="Restauration en cours…"
          onClick={async () => {
            const avant = await etatRestauration().catch(() => undefined)
            await api.post(`/sauvegardes/${encodeURIComponent(f.nom)}/restaurer`, {
              confirmation: mot.trim(),
              motif: motif.trim(),
            })
            onLancee(avant)
          }}
        >
          Restaurer maintenant
        </Bouton>
      </div>
    </>
  )
}

export function FenetreRestauration({ f, onFermer }: { f: FichierSauvegarde; onFermer: () => void }) {
  const client = useQueryClient()
  const [etape, setEtape] = useState<Etape>('lecture')
  const [avant, setAvant] = useState<string | undefined>(undefined)
  const [texte, setTexte] = useState('')
  useSuivi(etape === 'suivi', avant, (fin, lu) => {
    setTexte(lu)
    setEtape(fin)
    if (fin === 'faite') void client.invalidateQueries()
  })
  const occupe = etape === 'suivi'
  return (
    <Fenetre
      titre={`Restaurer la sauvegarde du ${horodatage(f.quand)}`}
      onFermer={occupe ? () => undefined : onFermer}
    >
      {etape === 'lecture' ? <Lecture f={f} onSuite={() => setEtape('mot')} onFermer={onFermer} /> : null}
      {etape === 'mot' ? (
        <Mot
          f={f}
          onFermer={onFermer}
          onLancee={(a) => {
            setAvant(a)
            setEtape('suivi')
          }}
        />
      ) : null}
      {etape === 'suivi' ? <Chargement quoi="la restauration (ne pas fermer la fenêtre)" /> : null}
      {etape === 'faite' ? (
        <Note ton="ok">
          {`La base est revenue à l’état du ${horodatage(f.quand)}. Les autres postes doivent rouvrir leur écran ; si la session est perdue, se reconnecter.`}
        </Note>
      ) : null}
      {etape === 'echec' ? (
        <Note ton="critique">{`La restauration a échoué : ${texte.replace(/^échec : /, '')}`}</Note>
      ) : null}
      {etape === 'faite' || etape === 'echec' ? (
        <div className={styles.rangee}>
          <span className={styles.pousse} />
          <Bouton variante="principal" onClick={onFermer}>
            Fermer
          </Bouton>
        </div>
      ) : null}
    </Fenetre>
  )
}
