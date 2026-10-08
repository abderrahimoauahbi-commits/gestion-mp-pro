/**
 * Un texte de `aide.json` à l'écran (`lib/aide.ts`) : gras, italique, et liens d'écran **filtrés
 * par rôle** (P1-19) — un écran que le rôle ne voit pas est nommé sans lien, avec « (réservé : …) ».
 */
import { Link } from 'react-router'

import { morceaux } from '../../lib/aide'
import { permis, rolesDe } from '../../lib/droits'
import type { Role } from '../../lib/types'
import { ecranDeAdresse } from '../../routes'
import styles from './TexteAide.module.css'

/** Un lien d'écran, ou son nom sans lien si le rôle ne l'ouvre pas. */
export function LienAide({ vers, role, children }: { vers: string; role: Role | null; children: string }) {
  if (role && permis(role, vers)) {
    return (
      <Link to={vers} className={styles.lien}>
        {children}
      </Link>
    )
  }
  const reserve = ecranDeAdresse(vers) ? rolesDe(vers) : ''
  return (
    <span className={styles.sansLien}>
      {children}
      {reserve && role ? <span className={styles.reserve}> (réservé : {reserve})</span> : null}
    </span>
  )
}

export function TexteAide({ texte, role }: { texte: string; role: Role | null }) {
  return (
    <>
      {morceaux(texte).map((m, i) => {
        if (m.genre === 'gras') return <strong key={i}>{m.texte}</strong>
        if (m.genre === 'italique') return <em key={i}>{m.texte}</em>
        if (m.genre === 'lien')
          return (
            <LienAide key={i} vers={m.vers} role={role}>
              {m.texte}
            </LienAide>
          )
        return <span key={i}>{m.texte}</span>
      })}
    </>
  )
}
