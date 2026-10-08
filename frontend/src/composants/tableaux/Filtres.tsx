/**
 * Les filtres d'une liste (A1, M75) : **liés** — chaque liste ne propose que les valeurs des
 * lignes qui passent les autres filtres (et la recherche), avec leur nombre ; « N critère(s) »
 * dès qu'un critère est posé ; « Effacer les filtres » dès deux critères (recherche comprise),
 * qui retire filtres et recherche.
 */
import { nombre } from '../../lib/format'
import { classes } from '../mise-en-page/classes'
import { Bouton } from '../saisie/Bouton'
import { nombreDeCriteres, optionsLiees, type Choix, type Filtre } from './filtrage'
import styles from './Filtres.module.css'

export interface FiltresProps<T> {
  filtres: readonly Filtre<T>[]
  lignes: readonly T[]
  choix: Choix
  onChoix: (cle: string, valeur: string | null) => void
  onEffacer: () => void
  /** La recherche est-elle posée (elle compte pour un critère) ? */
  recherchePosee?: boolean
  /** Les lignes que la recherche garde (les options suivent la recherche). */
  dansRecherche?: (ligne: T) => boolean
}

/** Le nombre de critères posés : filtres, et la recherche pour un. */
export function criteresPoses(choix: Choix, recherchePosee = false): number {
  return nombreDeCriteres(choix) + (recherchePosee ? 1 : 0)
}

export function Filtres<T>({
  filtres,
  lignes,
  choix,
  onChoix,
  onEffacer,
  recherchePosee,
  dansRecherche,
}: FiltresProps<T>) {
  const criteres = criteresPoses(choix, recherchePosee)
  return (
    <>
      {filtres.map((f) => {
        const pose = choix[f.cle] ?? ''
        return (
          <select
            key={f.cle}
            aria-label={f.libelle}
            className={classes(styles.filtre, pose && styles.pose)}
            value={pose}
            onChange={(e) => onChoix(f.cle, e.target.value || null)}
          >
            <option value="">{f.libelle} : tous</option>
            {optionsLiees(lignes, filtres, choix, f, dansRecherche).map((o) => (
              <option key={o.valeur} value={o.valeur}>
                {f.options ? o.libelle : `${o.libelle} (${nombre(o.nombre)})`}
              </option>
            ))}
          </select>
        )
      })}
      {criteres ? (
        <span className={styles.criteres}>
          {nombre(criteres)} critère{criteres > 1 ? 's' : ''}
        </span>
      ) : null}
      {criteres >= 2 ? (
        <Bouton taille="petit" variante="fantome" onClick={onEffacer}>
          Effacer les filtres
        </Bouton>
      ) : null}
    </>
  )
}
