/**
 * Le badge d'un statut, lu dans la table unique `lib/statuts.ts` (statut → libellé → ton) : un
 * statut ne se dit qu'à un endroit, jamais « Brouillon / Brouillon ». Une étiquette libre (hors
 * statut : « estimé », « prix du catalogue ») passe par `ton` et `children`.
 */
import type { ReactNode } from 'react'

import { statut, type Famille, type Ton } from '../../lib/statuts'
import { classes } from '../mise-en-page/classes'
import styles from './Badge.module.css'

export type BadgeProps =
  | { famille: Famille; valeur: string | null | undefined; titre?: string }
  | { ton: Ton; children: ReactNode; titre?: string }

export function Badge(props: BadgeProps) {
  const { libelle, ton } =
    'famille' in props ? statut(props.famille, props.valeur) : { libelle: props.children, ton: props.ton }
  return (
    <span className={classes(styles.badge, styles[ton])} title={props.titre} data-ton={ton}>
      {libelle}
    </span>
  )
}
