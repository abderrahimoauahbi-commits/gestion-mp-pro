/**
 * L'historique d'une fiche (`GET historique/{objet}/{id}`, API 51) : qui a fait quoi, quand, et
 * pour une modification les différences **avant → après** lisibles (nombres et dates à la
 * française, « — » pour un vide). Les prix sont déjà retirés par le serveur pour l'alimentation.
 */
import { date, horodatage, nombre, VIDE } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { Vide } from '../retour/Vide'
import styles from './Historique.module.css'

/** Une ligne d'historique (type provisoire, remplacé par `Schema<'LigneHistorique'>` à la publication). */
export interface LigneHistorique {
  id: number
  quand: string
  par: string
  action: string
  detail?: string | null
  changements?: { libelle: string; avant: unknown; apres: unknown }[]
}

/** Une valeur d'avant ou d'après, à la française. */
export function valeurLisible(v: unknown): string {
  if (v == null || v === '') return VIDE
  if (typeof v === 'number') return nombre(v, 0, 4)
  if (typeof v === 'boolean') return v ? 'oui' : 'non'
  if (typeof v === 'string') {
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return date(v)
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(v)) return horodatage(v)
    return v
  }
  return JSON.stringify(v)
}

export function Historique({ objet, id }: { objet: string; id: number }) {
  const lignes = useLecture<LigneHistorique[]>(`/historique/${objet}/${id}`)
  if (lignes.isPending) return <Chargement quoi="l’historique" />
  if (lignes.isError) return <Erreur erreur={lignes.error} onReessayer={() => void lignes.refetch()} />
  if (!lignes.data.length) return <Vide>Aucune modification enregistrée.</Vide>
  return (
    <ol className={styles.historique} aria-label="Historique">
      {lignes.data.map((l) => (
        <li key={l.id} className={styles.ligne}>
          <div className={styles.tete}>
            <strong>{l.action}</strong>
            <span className={styles.qui}>
              {horodatage(l.quand)} · {l.par}
            </span>
          </div>
          {l.detail ? <p className={styles.detail}>{l.detail}</p> : null}
          {l.changements?.length ? (
            <ul className={styles.changements}>
              {l.changements.map((c) => (
                <li key={c.libelle}>
                  {c.libelle} : <span className={styles.avant}>{valeurLisible(c.avant)}</span> →{' '}
                  <span className={styles.apres}>{valeurLisible(c.apres)}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </li>
      ))}
    </ol>
  )
}
