/**
 * L'aide d'un écran (A7), dans un tiroir par-dessus la page : ce que fait l'écran, ses règles, et
 * le chemin du Mode d'emploi. Le texte vient de `aide.json` (`ecran.<cle>`), comme la NOTICE.
 */
import { Link } from 'react-router'

import { AIDE_ECRANS } from '../../lib/aide'
import type { Role } from '../../lib/types'
import type { CleAide } from '../../routes'
import { Fenetre } from '../mise-en-page/Fenetre'
import styles from './AideEcran.module.css'
import { TexteAide } from './TexteAide'

export function AideEcran({
  cle,
  role,
  onFermer,
}: {
  cle: CleAide
  role: Role | null
  onFermer: () => void
}) {
  const aide = AIDE_ECRANS[cle]
  if (!aide) return null
  return (
    <Fenetre tiroir titre={`Aide — ${aide.titre}`} onFermer={onFermer}>
      <p className={styles.resume}>
        <TexteAide texte={aide.resume} role={role} />
      </p>
      {aide.points.length ? (
        <ul className={styles.points}>
          {aide.points.map((p) => (
            <li key={p}>
              <TexteAide texte={p} role={role} />
            </li>
          ))}
        </ul>
      ) : null}
      <p className={styles.suite}>
        <Link to="/aide" onClick={onFermer}>
          Tout le Mode d’emploi
        </Link>{' '}
        : les règles, qui fait quoi, les gestes pas à pas, les calculs.
      </p>
    </Fenetre>
  )
}
