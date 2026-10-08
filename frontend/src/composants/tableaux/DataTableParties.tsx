/** Les parties du `DataTable` : en-tête triable, corps (lignes cliquables, cellules-liens), pied de totaux. */
import type { KeyboardEvent, ReactNode } from 'react'
import { Link } from 'react-router'

import { classes } from '../mise-en-page/classes'
import { contenu, piedDeColonne, type Colonne } from './colonnes'
import styles from './DataTable.module.css'

export interface Tri {
  cle: string
  sens: 1 | -1
}

/** Le tri suivant au clic : croissant, décroissant, puis plus de tri. */
export function triSuivant(tri: Tri | null, cle: string): Tri | null {
  if (tri?.cle !== cle) return { cle, sens: 1 }
  return tri.sens === 1 ? { cle, sens: -1 } : null
}

export function Tete<T>({
  colonnes,
  tri,
  onTri,
}: {
  colonnes: readonly Colonne<T>[]
  tri: Tri | null
  onTri: (t: Tri | null) => void
}) {
  const clavier = (e: KeyboardEvent, c: Colonne<T>) => {
    if (e.key !== 'Enter' && e.key !== ' ') return
    e.preventDefault()
    onTri(triSuivant(tri, c.cle))
  }
  return (
    <thead>
      <tr>
        {colonnes
          .filter((c) => !c.cache)
          .map((c) => {
            const triable = c.triable !== false
            const sens = tri?.cle === c.cle ? tri.sens : 0
            return (
              <th
                key={c.cle}
                scope="col"
                className={classes(c.droite && styles.droite, triable && styles.triable)}
                style={c.largeur != null ? { width: c.largeur } : undefined}
                title={c.aide}
                tabIndex={triable ? 0 : undefined}
                aria-sort={sens === 1 ? 'ascending' : sens === -1 ? 'descending' : undefined}
                onClick={triable ? () => onTri(triSuivant(tri, c.cle)) : undefined}
                onKeyDown={triable ? (e) => clavier(e, c) : undefined}
              >
                {c.titre}
                {sens ? (
                  <span className={styles.sens} aria-hidden="true">
                    {sens === 1 ? '▲' : '▼'}
                  </span>
                ) : null}
              </th>
            )
          })}
      </tr>
    </thead>
  )
}

function Cellule<T>({ c, ligne }: { c: Colonne<T>; ligne: T }) {
  const lien = c.lien?.(ligne)
  const dedans = contenu(c, ligne)
  return (
    <td className={classes(c.droite && styles.droite, c.droite && 'nombre')}>
      {lien ? (
        <Link to={lien} onClick={(e) => e.stopPropagation()}>
          {dedans}
        </Link>
      ) : (
        dedans
      )}
    </td>
  )
}

export function Corps<T>(props: {
  colonnes: readonly Colonne<T>[]
  lignes: readonly T[]
  cle: (l: T) => string | number
  cliquable?: (l: T) => void
  marquee?: (l: T) => boolean
}) {
  const { colonnes, lignes, cle, cliquable, marquee } = props
  const visibles = colonnes.filter((c) => !c.cache)
  return (
    <tbody>
      {lignes.map((l) => (
        <tr
          key={cle(l)}
          className={classes(cliquable && styles.cliquable, marquee?.(l) && styles.marquee)}
          tabIndex={cliquable ? 0 : undefined}
          onClick={cliquable ? () => cliquable(l) : undefined}
          onKeyDown={
            cliquable
              ? (e) => {
                  if (e.key === 'Enter' && e.target === e.currentTarget) cliquable(l)
                }
              : undefined
          }
        >
          {visibles.map((c) => (
            <Cellule key={c.cle} c={c} ligne={l} />
          ))}
        </tr>
      ))}
    </tbody>
  )
}

export function Pied<T>({
  colonnes,
  lignes,
  pied,
}: {
  colonnes: readonly Colonne<T>[]
  lignes: readonly T[]
  pied?: ReactNode
}) {
  const visibles = colonnes.filter((c) => !c.cache)
  if (pied) return <tfoot>{pied}</tfoot>
  if (!lignes.length || !visibles.some((c) => c.total)) return null
  return (
    <tfoot>
      <tr>
        {visibles.map((c, i) => (
          <td key={c.cle} className={classes(c.droite && styles.droite, 'nombre')}>
            {c.total ? piedDeColonne(c, lignes) : i === 0 ? 'Total' : ''}
          </td>
        ))}
      </tr>
    </tfoot>
  )
}
