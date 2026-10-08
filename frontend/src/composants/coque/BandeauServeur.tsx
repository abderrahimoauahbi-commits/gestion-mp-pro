/**
 * Le bandeau de l'état du serveur (direction et administrateur technique) : sauvegarde en défaut
 * (rouge), base en retard de migration, base d'essai, HTTPS absent sur le réseau. Une base d'essai
 * se dit à tout le monde : on ne saisit pas le réel dans une base d'essai.
 */
import { nombre } from '../../lib/format'
import type { AlerteServeur } from '../../lib/types-provisoires-s2'
import type { Role } from '../../lib/types'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './BandeauServeur.module.css'

export interface PhraseServeur {
  texte: string
  ton: 'critique' | 'attention' | 'info'
}

/** Les phrases du bandeau pour ce rôle (vide : pas de bandeau). */
export function phrasesServeur(
  alerte: AlerteServeur | null | undefined,
  role: Role,
  baseEssai = false,
): PhraseServeur[] {
  const phrases: PhraseServeur[] = []
  const technique = role === 'direction' || role === 'administrateur'
  if (technique && alerte?.sauvegarde_en_defaut) {
    const age = alerte.sauvegarde_age_h
    phrases.push({
      ton: 'critique',
      texte:
        age == null
          ? 'Aucune sauvegarde de cette base : faites-en une dans Administration › Sauvegardes.'
          : `La dernière sauvegarde date de ${nombre(age)} h : vérifiez Administration › Sauvegardes.`,
    })
  }
  if (technique && alerte?.schema_en_retard)
    phrases.push({
      ton: 'critique',
      texte: 'La base est en retard sur cette version : la migration doit être faite.',
    })
  if (technique && alerte?.https_absent)
    phrases.push({
      ton: 'attention',
      texte: 'Le serveur est ouvert au réseau sans HTTPS : voir Administration › Serveur.',
    })
  if (baseEssai || alerte?.base_essai)
    phrases.push({ ton: 'info', texte: 'Base d’essai : rien de ce qui s’y saisit ne compte pour l’usine.' })
  return phrases
}

export function BandeauServeur({
  alerte,
  role,
  baseEssai,
}: {
  alerte: AlerteServeur | null | undefined
  role: Role
  baseEssai?: boolean
}) {
  const phrases = phrasesServeur(alerte, role, baseEssai)
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
