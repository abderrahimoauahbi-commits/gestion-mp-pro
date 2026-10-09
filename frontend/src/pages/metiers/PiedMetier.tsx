/**
 * Le pied de la fiche d'un métier : l'état de la saisie, « Supprimer » (direction, grisé avec sa
 * raison), « Annuler les modifications » / « Fermer », et « Enregistrer » grisé avec une raison qui
 * suit l'état, confirmé avec le texte unique de l'effet ((a)) et les alertes 30 jours.
 */
import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../composants/saisie/Bouton'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { nombre } from '../../lib/format'
import { etatPied } from './formeMetier'
import styles from './metiers.module.css'
import type { FicheMetierEtat } from './useFicheMetier'

/** La raison de griser « Supprimer » (refus du serveur dit d'avance). */
export function raisonSupprimer(e: FicheMetierEtat): string {
  if (e.m.fils.length) return 'Des fils y sont montés : les retirer d’abord'
  if (e.m.ordres) return `Nommé par ${nombre(e.m.ordres)} ordre(s) : l’arrêter plutôt (réglages)`
  return ''
}

function Question({ e }: { e: FicheMetierEtat }) {
  return (
    <>
      {e.message}{' '}
      {e.alertes.map((a) => (
        <strong key={a}>Attention : {a} </strong>
      ))}
      Enregistrer ?
    </>
  )
}

export function PiedMetier({
  e,
  direction,
  monteur,
}: {
  e: FicheMetierEtat
  direction: boolean
  monteur: boolean
}) {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied2}>
      <span className={styles.note}>{monteur ? etatPied(e.forme, e.initiale) : ''}</span>
      <span className={styles.pousse} />
      {direction ? (
        <Confirmer
          variante="danger"
          grise={raisonSupprimer(e) || undefined}
          question={`Supprimer le métier ${e.m.code} ?`}
          oui="Oui, supprimer"
          onOui={e.supprimer}
        >
          Supprimer
        </Confirmer>
      ) : null}
      {monteur && e.sale ? (
        <Confirmer
          question="Annuler les modifications ?"
          oui="Oui, annuler"
          onOui={() => e.repartir(e.base ?? e.m)}
        >
          Annuler les modifications
        </Confirmer>
      ) : (
        <Bouton onClick={fermer}>Fermer</Bouton>
      )}
      {monteur ? (
        <Confirmer
          variante="principal"
          grise={e.raison || undefined}
          question={<Question e={e} />}
          oui="Oui, enregistrer"
          attente="Enregistrement…"
          onOui={e.enregistrer}
        >
          Enregistrer
        </Confirmer>
      ) : null}
    </div>
  )
}
