/**
 * Se connecter (`/connexion`, hors coque, public) : toucher son nom puis taper son code (poste de
 * l'usine et téléphones enrôlés : GET /visages), ou taper son identifiant ailleurs (P1-26).
 * L'alimentation entre au 4e chiffre exactement (son code en a 4, H-01) ; les autres valident par
 * Entrée. Le motif d'une session perdue est dit en tête (P1-6, H-09) ; après la connexion, l'adresse
 * demandée est rouverte (`?retour=`).
 */
import { useState } from 'react'
import { Navigate, useLocation } from 'react-router'

import { EcranCentre } from '../../composants/coque/EcranCentre'
import { Chargement } from '../../composants/retour/Chargement'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { useLecture } from '../../lib/requetes'
import type { EtatInstallation, Visage } from '../../lib/types-coque'
import { TetePublique, useOublierLaSession } from './commun'
import styles from './connexion.module.css'
import { FormulaireIdentifiant, FormulaireVisages } from './Formulaires'

function motifDe(etat: unknown): string | null {
  if (typeof etat === 'object' && etat !== null && 'motif' in etat && typeof etat.motif === 'string')
    return etat.motif
  return null
}

function Panne({ onReessayer }: { onReessayer: () => void }) {
  return (
    <EcranCentre>
      <TetePublique titre="Gestion MP PRO" />
      <Note ton="critique">Le serveur ne répond pas. Vérifiez le réseau, puis rechargez la page.</Note>
      <Bouton onClick={onReessayer}>Réessayer</Bouton>
    </EcranCentre>
  )
}

export default function Connexion() {
  useOublierLaSession()
  const lieu = useLocation()
  const etat = useLecture<EtatInstallation>('/etat')
  const visages = useLecture<Visage[]>(etat.data?.installe ? '/visages' : null)
  const [parIdentifiant, setParIdentifiant] = useState(false)
  if (etat.isPending) return <Chargement quoi="Gestion MP PRO" />
  // Seule une réponse claire du serveur (« aucun compte ») mène à l'installation.
  if (etat.isError || typeof etat.data.installe !== 'boolean')
    return <Panne onReessayer={() => void etat.refetch()} />
  if (!etat.data.installe) return <Navigate to="/installation" replace />
  const motif = motifDe(lieu.state)
  const liste = visages.data ?? []
  const avecVisages = liste.length > 0 && !parIdentifiant
  return (
    <EcranCentre large={avecVisages}>
      <div className={styles.carte}>
        <TetePublique titre="Gestion MP PRO">
          {etat.data.societe || 'Matières premières'} —{' '}
          {avecVisages
            ? 'touchez votre nom, puis tapez votre code.'
            : 'tapez votre identifiant et votre code.'}
        </TetePublique>
        {motif ? <Note ton="attention">{motif}</Note> : null}
        {visages.isPending && etat.data.installe ? <Chargement quoi="les comptes" /> : null}
        {avecVisages ? <FormulaireVisages visages={liste} /> : null}
        {!avecVisages && !visages.isPending ? <FormulaireIdentifiant /> : null}
        {liste.length ? (
          <button type="button" className={styles.bascule} onClick={() => setParIdentifiant((v) => !v)}>
            {parIdentifiant ? 'Choisir mon nom' : 'Taper mon identifiant'}
          </button>
        ) : null}
        <p className={styles.pied}>
          Code oublié : la direction ou l’administrateur le remet à zéro dans Administration › Comptes.
        </p>
      </div>
    </EcranCentre>
  )
}
