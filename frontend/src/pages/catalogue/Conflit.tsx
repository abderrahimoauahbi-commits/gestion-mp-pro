/**
 * Une fiche modifiée entre-temps sur un autre poste (R2, P7-14) : le serveur refuse l'écriture
 * (409 `conflit_version`, « Cette matière a été modifiée entre-temps par Nadia (…) ») ; la fiche
 * le dit au-dessus de la saisie, avec « Recharger la fiche ». Rien n'est perdu sans le vouloir :
 * recharger remplace la saisie par la dernière version, et le dit.
 */
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { ErreurApi } from '../../lib/api'
import styles from './catalogue.module.css'

/** Le message du serveur si l'erreur est un conflit de version, sinon `null`. */
export function messageConflit(e: unknown): string | null {
  return e instanceof ErreurApi && e.code === 'conflit_version' ? e.message : null
}

/** Ce que dit l'écran une fois la fiche rechargée. */
export const RECHARGEE = 'Fiche rechargée dans sa dernière version : refaire la modification.'

export function BandeauConflit({
  message,
  onRecharger,
  libelle = 'Recharger la fiche',
}: {
  message: string | null
  onRecharger: () => unknown
  libelle?: string
}) {
  if (!message) return null
  return (
    <div className={styles.conflit} role="alert">
      <Note ton="attention">
        <strong>{message}</strong>
        <br />
        La fiche affichée n’est plus la dernière : la recharger avant de modifier.
      </Note>
      <Bouton variante="principal" attente="Lecture…" onClick={onRecharger}>
        {libelle}
      </Bouton>
    </div>
  )
}
