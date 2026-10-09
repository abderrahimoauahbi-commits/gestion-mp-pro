/**
 * Les petites briques communes aux onglets de l'Analyse (et réemployées par les Réglages et
 * l'Administration) : une liste de choix dans la barre d'outils d'un tableau, une case, et
 * « Effacer les filtres » pour les listes dont les critères ne sont pas des filtres de colonne
 * (date, case, fenêtre) — dès deux critères, recherche comprise (A1).
 */
import type { ReactNode } from 'react'

import { classes } from '../../composants/mise-en-page/classes'
import { Bouton } from '../../composants/saisie/Bouton'
import filtres from '../../composants/tableaux/Filtres.module.css'
import { nombre } from '../../lib/format'
import styles from './analyse.module.css'

export interface OptionListe {
  valeur: string
  libelle: string
  titre?: string
}

/** Une liste de choix de la barre d'outils ; « posée » (marquée) hors de sa valeur par défaut. */
export function ChoixListe({
  libelle,
  valeur,
  options,
  onChange,
  defaut = '',
  titre,
}: {
  libelle: string
  valeur: string
  options: readonly OptionListe[]
  onChange: (valeur: string) => void
  defaut?: string
  titre?: string
}) {
  return (
    <select
      aria-label={libelle}
      title={titre ?? options.find((o) => o.valeur === valeur)?.titre}
      className={classes(filtres.filtre, valeur !== defaut && filtres.pose)}
      value={valeur}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o.valeur} value={o.valeur} title={o.titre}>
          {o.libelle}
        </option>
      ))}
    </select>
  )
}

/** Une case à cocher de la barre d'outils (« seulement les anomalies »). */
export function Case({
  valeur,
  onChange,
  children,
  titre,
}: {
  valeur: boolean
  onChange: (v: boolean) => void
  children: ReactNode
  titre?: string
}) {
  return (
    <label className={styles.case} title={titre}>
      <input type="checkbox" checked={valeur} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  )
}

/** « N critère(s) » et « Effacer les filtres » (dès deux), pour une liste sans filtre de colonne. */
export function Criteres({ nombre: n, onEffacer }: { nombre: number; onEffacer: () => void }) {
  return (
    <>
      {n ? (
        <span className={filtres.criteres}>
          {nombre(n)} critère{n > 1 ? 's' : ''}
        </span>
      ) : null}
      {n >= 2 ? (
        <Bouton taille="petit" variante="fantome" onClick={onEffacer}>
          Effacer les filtres
        </Bouton>
      ) : null}
    </>
  )
}

/** Une cellule sur deux lignes : la valeur, et sa précision dessous (référence et fournisseur…). */
export function Deux({
  haut,
  bas,
  titre,
  coupe,
}: {
  haut: ReactNode
  bas?: ReactNode
  titre?: string
  coupe?: boolean
}) {
  return (
    <>
      <span className={coupe ? styles.ref : undefined} title={titre}>
        {haut}
      </span>
      {bas ? <span className={styles.dessous}>{bas}</span> : null}
    </>
  )
}
