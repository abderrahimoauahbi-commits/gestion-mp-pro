/**
 * Un nombre saisi à la française (ECRANS-PRO § 3) : virgule ou point pour les décimales, espaces
 * des milliers ignorés, « − » accepté. Hors saisie, il s'affiche avec ses milliers
 * (« 1 234,5 ») ; au focus, tout est sélectionné (taper remplace, comme dans un tableur) et un
 * champ à zéro s'ouvre vide (« 139 » ne devient pas « 0139 »). Pas de `type=number` : la molette
 * ne change pas un prix en passant.
 *
 * Les bornes et le nombre de décimales sont **contrôlés à la frappe** : le message s'écrit sous
 * le champ (`messageNombre`, que la page reprend dans le `manque` de son bouton).
 */
import { useId, useRef, useState, type ChangeEvent, type FocusEvent } from 'react'

import { nombre } from '../../lib/format'
import { classes } from '../mise-en-page/classes'
import { attributsDuChamp, useChamp } from './Champ'
import styles from './controle.module.css'

/** Le nombre d'un texte tapé : `null` si vide, `undefined` si ce n'est pas un nombre. */
export function lireNombre(texte: string): number | null | undefined {
  const propre = texte.replace(/[\s\u00a0\u202f]/g, '').replace('−', '-')
  if (propre === '') return null
  if (!/^-?(\d+([.,]\d*)?|[.,]\d+)$/.test(propre)) return undefined
  return Number(propre.replace(',', '.'))
}

/** Le texte d'un nombre à modifier : sans milliers, virgule décimale. */
export function texteDeSaisie(valeur: number | null): string {
  return valeur == null || valeur === 0 ? '' : String(valeur).replace('.', ',')
}

export interface BornesNombre {
  min?: number
  max?: number
  decimales?: number
}

/** Ce qui ne va pas dans un nombre au regard de ses bornes, ou '' . */
export function messageNombre(
  valeur: number | null | undefined,
  { min, max, decimales }: BornesNombre,
): string {
  if (valeur === undefined) return 'Un nombre est attendu (virgule pour les décimales).'
  if (valeur == null) return ''
  if (min != null && valeur < min) return `Au moins ${nombre(min, 0, 4)}.`
  if (max != null && valeur > max) return `Au plus ${nombre(max, 0, 4)}.`
  if (decimales != null) {
    const partie = String(valeur).split('.')[1] ?? ''
    if (partie.length > decimales)
      return decimales === 0
        ? 'Un nombre entier est attendu.'
        : `${decimales} décimale${decimales > 1 ? 's' : ''} au plus.`
  }
  return ''
}

export interface NombreProps extends BornesNombre {
  valeur: number | null
  onChange: (valeur: number | null) => void
  unite?: string
  /** 100 pour saisir en pourcent une fraction (0,25 s'écrit « 25 »). */
  echelle?: number
  placeholder?: string
  desactive?: boolean
  libelle?: string
  className?: string
}

/**
 * La frappe d'un nombre, commune à `Nombre` et au `Compteur` de l'atelier : le texte tapé est
 * gardé tel quel pendant la saisie (« 0, », « − »), tout est sélectionné juste après le focus
 * (sauf si la frappe a déjà commencé), et chaque texte lisible remonte en nombre.
 */
export function useFrappeNombre(affiche: number | null, onChange: (v: number | null) => void, echelle = 1) {
  const [texte, setTexte] = useState<string | null>(null)
  const selection = useRef(0)
  const lu = texte == null ? affiche : lireNombre(texte)
  const proprietes = {
    inputMode: 'decimal' as const,
    autoComplete: 'off',
    onFocus: (e: FocusEvent<HTMLInputElement>) => {
      setTexte(texteDeSaisie(affiche))
      const cible = e.currentTarget
      selection.current = requestAnimationFrame(() => cible.select())
    },
    onBlur: () => setTexte(null),
    onChange: (e: ChangeEvent<HTMLInputElement>) => {
      cancelAnimationFrame(selection.current)
      setTexte(e.target.value)
      const v = lireNombre(e.target.value)
      if (v !== undefined) onChange(v == null ? null : v / echelle)
    },
  }
  return { texte, lu, oublier: () => setTexte(null), proprietes }
}

export function Nombre({
  valeur,
  onChange,
  unite,
  echelle = 1,
  placeholder,
  desactive,
  libelle,
  className,
  ...bornes
}: NombreProps) {
  const liens = useChamp()
  const id = useId()
  const affiche = valeur == null ? null : valeur * echelle
  const frappe = useFrappeNombre(affiche, onChange, echelle)
  const fois = (b?: number) => (b == null ? undefined : b * echelle)
  const message = messageNombre(frappe.lu, {
    min: fois(bornes.min),
    max: fois(bornes.max),
    decimales: bornes.decimales,
  })
  const champ = (
    <input
      {...attributsDuChamp(liens, message ? id : undefined, libelle)}
      {...frappe.proprietes}
      aria-invalid={message ? true : liens?.invalide || undefined}
      className={classes(styles.controle, styles.nombre, className)}
      placeholder={placeholder}
      disabled={desactive}
      value={frappe.texte ?? (affiche == null ? '' : nombre(affiche, 0, Math.max(bornes.decimales ?? 4, 0)))}
    />
  )
  return (
    <>
      {unite ? (
        <span className={styles.avecUnite}>
          {champ}
          <span className={styles.unite}>{unite}</span>
        </span>
      ) : (
        champ
      )}
      {message ? (
        <span id={id} className={styles.message}>
          {message}
        </span>
      ) : null}
    </>
  )
}
