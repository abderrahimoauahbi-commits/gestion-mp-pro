/**
 * Première installation (`/installation`, public tant qu'aucun compte n'existe) : la société et le
 * compte de la direction, qui crée ensuite les autres (Administration › Comptes). POST /installation
 * (route 9) ; ensuite, entrée au Cockpit. Déjà installé : retour à la connexion.
 */
import { useState, type FormEvent } from 'react'
import { Link, Navigate } from 'react-router'

import { EcranCentre } from '../../composants/coque/EcranCentre'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ, erreurDuChamp } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { api, ErreurApi, messageErreur } from '../../lib/api'
import { sansAccents } from '../../lib/recherche'
import { useLecture } from '../../lib/requetes'
import type { EtatInstallation, Installation as CorpsInstallation, Moi } from '../../lib/types-coque'
import { TetePublique, useEntrer } from './commun'
import styles from './connexion.module.css'

/** L'identifiant tiré d'un nom (« Karim Benali » → « karim.benali »), en minuscules sans accents. */
export function identifiantDe(nom: string): string {
  return sansAccents(nom)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '.')
    .replace(/^\.+|\.+$/g, '')
    .slice(0, 40)
}

/** Ce qui manque avant de créer le compte. */
export function manqueInstallation(nom: string, code: string): string[] {
  const manque: string[] = []
  if (nom.trim().length < 2) manque.push('votre nom (2 caractères au moins)')
  if (code.length < 8) manque.push('un code de 8 caractères au moins')
  return manque
}

/** POST /installation, puis l'entrée au Cockpit ; le refus est gardé pour être dit. */
function useInstaller() {
  const entrer = useEntrer()
  const [refus, setRefus] = useState<unknown>(null)
  const [occupe, setOccupe] = useState(false)
  const installer = async (corps: CorpsInstallation) => {
    if (occupe) return
    setOccupe(true)
    setRefus(null)
    try {
      entrer(await api.post<Moi>('/installation', corps))
    } catch (x) {
      setRefus(x)
    } finally {
      setOccupe(false)
    }
  }
  return { refus, occupe, installer }
}

function Formulaire() {
  const [societe, setSociete] = useState('')
  const [nom, setNom] = useState('')
  const [identifiant, setIdentifiant] = useState('')
  const [code, setCode] = useState('')
  const retenu = identifiantDe(identifiant || nom)
  const manque = manqueInstallation(nom, code)
  const { refus, occupe, installer } = useInstaller()
  const soumettre = (e: FormEvent) => {
    e.preventDefault()
    if (manque.length) return
    void installer({ societe: societe.trim(), nom: nom.trim(), identifiant: retenu, code })
  }
  const deja = refus instanceof ErreurApi && refus.statut === 409
  return (
    <form className={styles.formulaire} onSubmit={soumettre}>
      <Champ libelle="Société" erreur={erreurDuChamp(refus, 'societe')}>
        <Saisie valeur={societe} onChange={setSociete} max={160} autoFocus />
      </Champ>
      <Champ libelle="Votre nom" obligatoire erreur={erreurDuChamp(refus, 'nom')}>
        <Saisie valeur={nom} onChange={setNom} max={80} placeholder="MAZARI" />
      </Champ>
      <Champ
        libelle="Identifiant"
        aide={
          retenu
            ? `Ce qui vous désigne à la connexion. Retenu : « ${retenu} ».`
            : 'Ce qui vous désigne à la connexion.'
        }
        erreur={erreurDuChamp(refus, 'identifiant')}
      >
        <Saisie
          valeur={identifiant}
          onChange={setIdentifiant}
          max={40}
          placeholder="mazari"
          autoComplete="username"
        />
      </Champ>
      <Champ libelle="Code" obligatoire aide="8 caractères au moins." erreur={erreurDuChamp(refus, 'code')}>
        <Saisie valeur={code} onChange={setCode} type="password" autoComplete="new-password" />
      </Champ>
      {refus ? (
        <Note ton="critique">
          {messageErreur(refus)} {deja ? <Link to="/connexion">Se connecter</Link> : null}
        </Note>
      ) : null}
      <div className={styles.gestes}>
        <Bouton type="submit" variante="principal" manque={manque} occupe={occupe} attente="Création…">
          Créer le compte et entrer
        </Bouton>
      </div>
    </form>
  )
}

export default function Installation() {
  const etat = useLecture<EtatInstallation>('/etat')
  if (etat.isPending) return <Chargement quoi="Gestion MP PRO" />
  if (etat.data?.installe) return <Navigate to="/connexion" replace />
  return (
    <EcranCentre>
      <div className={styles.carte}>
        <TetePublique titre="Bienvenue dans Gestion MP PRO">
          Premier lancement : créez le compte de la direction. Il ouvre tout, et crée ensuite les comptes des
          achats, de l’alimentation des machines et de l’administrateur technique (Administration › Comptes).
        </TetePublique>
        {etat.isError ? (
          <Note ton="critique">Le serveur ne répond pas. Vérifiez le réseau, puis rechargez la page.</Note>
        ) : (
          <Formulaire />
        )}
      </div>
    </EcranCentre>
  )
}
