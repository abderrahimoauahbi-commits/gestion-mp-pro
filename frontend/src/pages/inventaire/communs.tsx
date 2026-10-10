/**
 * Les cellules partagées par la liste et le comptage : écart en kilos signé et coloré par son
 * signe (an. 23, même règle dans les deux onglets), valeur de l'écart en dirhams avec « sans
 * signe », badge « Hors tolérance » à la règle unique.
 */
import { Badge } from '../../composants/retour/Badge'
import { classes } from '../../composants/mise-en-page/classes'
import { montant, nombre, nombreSigne, VIDE } from '../../lib/format'
import styles from './Inventaire.module.css'
import { POUSSIERE, tonHorsTolerance } from './types'

/** « +12,5 kg » en vert, « −3,0 kg » en rouge, « 0,0 » sans couleur ; `null` : « — ». */
export function EcartKg({ valeur, colore = true }: { valeur: number | null | undefined; colore?: boolean }) {
  if (valeur == null) return <span className="nombre">{VIDE}</span>
  const signe = valeur <= -POUSSIERE ? styles.negatif : valeur >= POUSSIERE ? styles.positif : undefined
  return <span className={classes('nombre', colore && signe)}>{nombreSigne(valeur, 0, 2)}</span>
}

/** La valeur nette de l'écart en MAD, et « {abs} sans signe » dessous. */
export function ValeurEcart({ net, absolu }: { net: number | null | undefined; absolu?: number | null }) {
  if (net == null) return <span className="nombre">{VIDE}</span>
  return (
    <span className={styles.valeur}>
      <span className="nombre">{nombreSigne(net, 0)}&nbsp;MAD</span>
      {absolu != null && Math.abs(absolu - Math.abs(net)) >= 1 ? (
        <span className={styles.note}>{montant(absolu, 'MAD')} sans signe</span>
      ) : null}
    </span>
  )
}

/** Le nombre d'écarts hors tolérance, au ton de la règle unique. */
export function BadgeHorsTolerance({ hors, sansJustification }: { hors: number; sansJustification: number }) {
  const titre =
    sansJustification > 0
      ? `${nombre(sansJustification)} sans justification`
      : hors > 0
        ? 'tous justifiés'
        : 'aucun écart hors tolérance'
  return (
    <Badge ton={tonHorsTolerance(hors, sansJustification)} titre={titre}>
      {nombre(hors)}
    </Badge>
  )
}
