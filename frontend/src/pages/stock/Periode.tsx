/**
 * « Du » et « Au » d'une liste, dans l'adresse avec ses filtres (comptés dans « N critère(s) »,
 * retirés par « Effacer les filtres ») ; « Du » ne passe pas « Au ».
 */
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import styles from './stock.module.css'

export function Periode({
  choix,
  du = 'du',
  au = 'au',
}: {
  choix: EtatTable['choix']
  du?: string
  au?: string
}) {
  const debut = choix.valeurs[du] ?? ''
  const fin = choix.valeurs[au] ?? ''
  return (
    <>
      <label className={styles.case}>
        Du
        <input
          type="date"
          className={styles.champDate}
          value={debut}
          max={fin || undefined}
          onChange={(e) => choix.poser(du, e.target.value || null)}
        />
      </label>
      <label className={styles.case}>
        Au
        <input
          type="date"
          className={styles.champDate}
          value={fin}
          min={debut || undefined}
          onChange={(e) => choix.poser(au, e.target.value || null)}
        />
      </label>
    </>
  )
}
