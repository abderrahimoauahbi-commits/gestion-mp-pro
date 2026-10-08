/** « Un instant — chargement : {quoi}… » : un chargement honnête, jamais un faux « n'existe plus ». */
import styles from './Chargement.module.css'

export function Chargement({ quoi = 'les données' }: { quoi?: string }) {
  return (
    <div className={styles.chargement} role="status" aria-live="polite">
      <span className={styles.roue} aria-hidden="true" />
      Un instant — chargement : {quoi}…
    </div>
  )
}
