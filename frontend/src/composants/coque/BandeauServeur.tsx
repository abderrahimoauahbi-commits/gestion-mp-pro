/**
 * Le bandeau de l'état du serveur : l'alerte du serveur (`contexte.alerte_serveur`, une phrase,
 * rendue à la direction et à l'administrateur seulement : sauvegarde en défaut, base en retard,
 * écoute réseau sans HTTPS…) en rouge ; une base d'essai se dit à tout le monde (on ne saisit pas
 * le réel dans une base d'essai).
 */
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './BandeauServeur.module.css'

export interface PhraseServeur {
  texte: string
  ton: 'critique' | 'info'
}

/** Les phrases du bandeau (vide : pas de bandeau). */
export function phrasesServeur(alerte: string | null | undefined, baseEssai = false): PhraseServeur[] {
  const phrases: PhraseServeur[] = []
  if (alerte?.trim()) phrases.push({ ton: 'critique', texte: alerte.trim() })
  if (baseEssai)
    phrases.push({ ton: 'info', texte: 'Base d’essai : rien de ce qui s’y saisit ne compte pour l’usine.' })
  return phrases
}

export function BandeauServeur({
  alerte,
  baseEssai,
}: {
  alerte: string | null | undefined
  baseEssai?: boolean
}) {
  const phrases = phrasesServeur(alerte, baseEssai)
  if (!phrases.length) return null
  return (
    <div className={styles.bandeau} role="status">
      {phrases.map((p) => (
        <p key={p.texte} className={classes(styles.phrase, styles[p.ton])}>
          <Icone nom={p.ton === 'info' ? 'info' : 'attention'} />
          {p.texte}
        </p>
      ))}
    </div>
  )
}
