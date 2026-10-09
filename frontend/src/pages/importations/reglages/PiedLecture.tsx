/** Le pied d'une fenêtre de réglage lue par les achats : « Fermer » seul, aucun geste d'écriture. */
import { useFermerFenetre } from '../../../composants/mise-en-page/Fenetre'
import { Bouton } from '../../../composants/saisie/Bouton'
import styles from './reglages.module.css'

export function PiedLecture() {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied}>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Fermer</Bouton>
    </div>
  )
}
