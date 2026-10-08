/**
 * Une date (JJ/MM/AAAA à l'écran, AAAA-MM-JJ échangée). Bornée : `max` est **aujourd'hui à
 * l'heure du serveur** par défaut (un jalon constaté, une réception, une sortie ne sont jamais
 * dans le futur) ; `min` est le lendemain de la période close quand le document en dépend. Une
 * date hors bornes est dite à la frappe, avec sa raison, au lieu d'attendre le refus du serveur.
 * `futurPermis` lève la borne haute (livraison prévue, échéance).
 */
import { useId } from 'react'

import { date } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { classes } from '../mise-en-page/classes'
import { attributsDuChamp, useChamp } from './Champ'
import styles from './controle.module.css'

/** Ce qui ne va pas dans une date au regard de ses bornes, ou ''. */
export function messageDate(valeur: string, min?: string, max?: string, raisonMin?: string): string {
  if (!valeur) return ''
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valeur)) return 'Date incomplète.'
  if (max && valeur > max) {
    return max === aujourdhui()
      ? `Au plus tard aujourd'hui (${date(max)}) : pas de date dans le futur.`
      : `Au plus tard le ${date(max)}.`
  }
  if (min && valeur < min) return `Au plus tôt le ${date(min)}${raisonMin ? ` : ${raisonMin}` : ''}.`
  return ''
}

export interface DateChampProps {
  valeur: string
  onChange: (valeur: string) => void
  min?: string
  max?: string
  futurPermis?: boolean
  /** Pourquoi pas avant `min` (« la période est close jusqu'au 30/09/2026 »). */
  raisonMin?: string
  libelle?: string
  desactive?: boolean
}

export function DateChamp({
  valeur,
  onChange,
  min,
  max,
  futurPermis,
  raisonMin,
  libelle,
  desactive,
}: DateChampProps) {
  const liens = useChamp()
  const id = useId()
  const borneHaute = futurPermis ? max : (max ?? aujourdhui())
  const message = messageDate(valeur, min, borneHaute, raisonMin)
  return (
    <>
      <input
        {...attributsDuChamp(liens, message ? id : undefined, libelle)}
        aria-invalid={message ? true : liens?.invalide || undefined}
        type="date"
        className={classes(styles.controle)}
        value={valeur}
        min={min}
        max={borneHaute}
        disabled={desactive}
        onChange={(e) => onChange(e.target.value)}
      />
      {message ? (
        <span id={id} className={styles.message}>
          {message}
        </span>
      ) : null}
    </>
  )
}
