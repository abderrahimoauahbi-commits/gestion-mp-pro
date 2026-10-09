/**
 * Les critères de l'onglet « Par matière » qu'un filtre à une valeur ne dit pas : le magasin (une
 * matière peut être dans plusieurs), « En stock », « À commander » (direction et achats). Ils
 * vivent dans l'adresse avec les autres filtres et comptent dans « N critère(s) » ; « Effacer les
 * filtres » les retire aussi.
 */
import { classes } from '../../composants/mise-en-page/classes'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import styles from './stock.module.css'

export function FiltresCases({
  table,
  magasins,
  aCommander,
}: {
  table: EtatTable
  magasins: readonly string[]
  aCommander: boolean
}) {
  const v = table.choix.valeurs
  const poser = (cle: string, oui: boolean) => table.choix.poser(cle, oui ? '1' : null)
  return (
    <>
      <select
        aria-label="Magasin"
        title="Les matières qui ont du stock dans ce magasin"
        className={classes(styles.selecteur, v.magasin && styles.selecteurPose)}
        value={v.magasin ?? ''}
        onChange={(e) => table.choix.poser('magasin', e.target.value || null)}
      >
        <option value="">Magasin : tous</option>
        {magasins.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      <label className={styles.case}>
        <input
          type="checkbox"
          checked={v.en_stock === '1'}
          onChange={(e) => poser('en_stock', e.target.checked)}
        />
        En stock
      </label>
      {aCommander ? (
        <label className={styles.case} title="Les matières pour lesquelles le calcul propose une commande">
          <input
            type="checkbox"
            checked={v.a_commander === '1'}
            onChange={(e) => poser('a_commander', e.target.checked)}
          />
          À commander
        </label>
      ) : null}
    </>
  )
}
