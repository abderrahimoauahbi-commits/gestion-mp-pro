/**
 * La barre du bas de l'atelier : Accueil, Envoyer, Retour, Lots — toujours là, cases de 44 px
 * au moins, case active marquée. Changer d'écran ne perd pas la saisie (`useSaisieGardee`).
 */
import { NavLink } from 'react-router'

import { classes } from '../mise-en-page/classes'
import { Icone, type NomIcone } from '../mise-en-page/Icone'
import styles from './BarreBas.module.css'

export const CASES: readonly { vers: string; libelle: string; icone: NomIcone; exact?: boolean }[] = [
  { vers: '/atelier', libelle: 'Accueil', icone: 'accueil', exact: true },
  { vers: '/atelier/envoyer', libelle: 'Envoyer', icone: 'envoyer' },
  { vers: '/atelier/retour', libelle: 'Retour', icone: 'retour' },
  { vers: '/atelier/chercher', libelle: 'Lots', icone: 'lots' },
]

export function BarreBas() {
  return (
    <nav className={styles.barre} aria-label="Atelier">
      {CASES.map((c) => (
        <NavLink
          key={c.vers}
          to={c.vers}
          end={c.exact}
          className={({ isActive }) => classes(styles.case, isActive && styles.active)}
        >
          <Icone nom={c.icone} taille={22} />
          <span>{c.libelle}</span>
        </NavLink>
      ))}
    </nav>
  )
}
