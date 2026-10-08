/**
 * Une page du bureau (ECRANS-PRO § 1) : `EnTete` (coque, lot E2), une rangée d'`Indicateurs`,
 * des `Onglets`, une `Carte` dont le tableau prend la hauteur restante (`Cadre`). La page ne
 * défile jamais en 1366 × 768 : elle remplit le `<main>` de la coque, et seul le cadre défile.
 *
 * Elle pose le titre de l'onglet du navigateur : « Commandes — Gestion MP PRO ».
 */
import { useEffect, type ReactNode } from 'react'

import styles from './Page.module.css'

/** Le nom de l'application, en fin de titre d'onglet du navigateur. */
export const NOM_APPLICATION = 'Gestion MP PRO'

export function titreDOnglet(titre: string): string {
  return titre ? `${titre} — ${NOM_APPLICATION}` : NOM_APPLICATION
}

export function Page({ titre, children }: { titre: string; children: ReactNode }) {
  useEffect(() => {
    const avant = document.title
    document.title = titreDOnglet(titre)
    return () => {
      document.title = avant
    }
  }, [titre])
  return <div className={styles.page}>{children}</div>
}
