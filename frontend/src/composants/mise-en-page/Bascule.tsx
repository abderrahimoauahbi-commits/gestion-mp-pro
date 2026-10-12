/**
 * Deux à six vues d'une même carte, dans son en-tête (les écrans, eux, se découpent en
 * `Onglets`). La vue vit dans l'adresse (`?vue=`, P2-5) avec `useVueAdresse`.
 */
import { useCallback } from 'react'
import { useSearchParams } from 'react-router'

import { avecParametre } from '../../lib/adresse'
import { classes } from './classes'
import styles from './Bascule.module.css'

export interface Vue<T extends string> {
  cle: T
  libelle: string
  titre?: string
}

export function Bascule<T extends string>({
  vues,
  valeur,
  onChange,
  libelle = 'Vue',
}: {
  vues: readonly Vue<T>[]
  valeur: T
  onChange: (cle: T) => void
  libelle?: string
}) {
  if (vues.length < 2 || vues.length > 6) {
    console.error(`Bascule « ${libelle} » : 2 à 6 vues (${vues.length}) ; au-delà, des onglets.`)
  }
  return (
    <div className={styles.bascule} role="group" aria-label={libelle}>
      {vues.map((v) => (
        <button
          key={v.cle}
          type="button"
          aria-pressed={v.cle === valeur}
          title={v.titre}
          className={classes(styles.vue, v.cle === valeur && styles.actif)}
          onClick={() => onChange(v.cle)}
        >
          {v.libelle}
        </button>
      ))}
    </div>
  )
}

/** La vue d'une bascule, dans `?vue=` (la vue par défaut n'écrit rien). */
export function useVueAdresse<T extends string>(permises: readonly T[], defaut: T): [T, (vue: T) => void] {
  const [params, setParams] = useSearchParams()
  const lue = params.get('vue')
  const vue = permises.find((p) => p === lue) ?? defaut
  const choisir = useCallback(
    (v: T) => setParams((p) => avecParametre(p, 'vue', v === defaut ? null : v), { replace: true }),
    [setParams, defaut],
  )
  return [vue, choisir]
}
