/**
 * Une lecture qui a échoué. « Pas de réseau » se dit comme tel (statut 0 : le serveur n'a pas
 * répondu), distinct d'une liste vide et d'un refus, avec « Réessayer » ; un refus du serveur est
 * dit tel quel. Rien si `erreur` est vide.
 */
import { ErreurApi, messageErreur } from '../../lib/api'
import { Bouton } from '../saisie/Bouton'
import styles from './Erreur.module.css'

/** Vrai pour une erreur de réseau (le serveur n'a pas répondu, ou le relais dit qu'il est arrêté). */
export function estPasDeReseau(erreur: unknown): boolean {
  return erreur instanceof ErreurApi && (erreur.statut === 0 || erreur.code === 'serveur_absent')
}

export function Erreur({
  erreur,
  onReessayer,
  tactile,
}: {
  erreur: unknown
  onReessayer?: () => void
  tactile?: boolean
}) {
  if (erreur == null || erreur === '') return null
  const reseau = estPasDeReseau(erreur)
  return (
    <div className={styles.erreur} role="alert">
      <strong className={styles.titre}>{reseau ? 'Pas de réseau' : 'La lecture a échoué'}</strong>
      <span>
        {reseau ? 'Le serveur ne répond pas : vérifiez le Wi-Fi ou la 4G/5G.' : messageErreur(erreur)}
      </span>
      {onReessayer ? (
        <Bouton taille={tactile ? 'atelier' : 'petit'} onClick={onReessayer}>
          Réessayer
        </Bouton>
      ) : null}
    </div>
  )
}
