/**
 * Enrôler un téléphone (`/enroler?jeton=…`, public) : l'adresse du QR à usage unique créé dans
 * Administration › Appareils. POST /appareils/enroler (route 22) pose le cookie d'appareil ; la
 * connexion montre ensuite les visages sur cet appareil.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { EcranCentre } from '../../composants/coque/EcranCentre'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { api, messageErreur } from '../../lib/api'
import { TetePublique } from './commun'
import styles from './connexion.module.css'

type Etat = { genre: 'envoi' } | { genre: 'fait' } | { genre: 'refus'; message: string }

export default function Enroler() {
  const [params] = useSearchParams()
  const jeton = params.get('jeton') ?? ''
  const [etat, setEtat] = useState<Etat>(
    jeton
      ? { genre: 'envoi' }
      : { genre: 'refus', message: 'Ce lien d’enrôlement est incomplet : lisez de nouveau le QR.' },
  )
  const envoye = useRef(false)
  useEffect(() => {
    // Un jeton ne sert qu'une fois : un seul envoi, même si l'écran se monte deux fois.
    if (!jeton || envoye.current) return
    envoye.current = true
    api
      .post<void>('/appareils/enroler', { jeton })
      .then(() => setEtat({ genre: 'fait' }))
      .catch((e: unknown) => setEtat({ genre: 'refus', message: messageErreur(e) }))
  }, [jeton])
  return (
    <EcranCentre>
      <div className={styles.carte}>
        <TetePublique titre="Enrôler ce téléphone" />
        {etat.genre === 'envoi' ? <Chargement quoi="l’enrôlement" /> : null}
        {etat.genre === 'fait' ? (
          <Note ton="ok">Ce téléphone est enrôlé : la connexion y montre maintenant les visages.</Note>
        ) : null}
        {etat.genre === 'refus' ? <Note ton="critique">{etat.message}</Note> : null}
        <Link to="/connexion">Aller à la connexion</Link>
      </div>
    </EcranCentre>
  )
}
