/**
 * L'avant et l'après d'une entrée du journal, lisibles : « champ : valeur · … », nombres à la
 * française, dates « jj/mm/aaaa », oui / non, « — » pour vide (P8-13, P8-14). Les clés sont
 * celles du serveur, rendues plus lisibles (`_` → espace).
 */
import { date, horodatage, nombre, VIDE } from '../../lib/format'

/** Une valeur d'un changement, à la française. */
export function valeurLisible(v: unknown): string {
  if (v == null || v === '') return VIDE
  if (typeof v === 'boolean') return v ? 'oui' : 'non'
  if (typeof v === 'number') return nombre(v, 0, 4)
  if (typeof v === 'string') {
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return date(v)
    if (/^\d{4}-\d{2}-\d{2}T/.test(v)) return horodatage(v)
    if (/^-?\d+\.\d+$/.test(v)) return nombre(Number(v), 0, 4)
    return v
  }
  if (Array.isArray(v)) return v.map(valeurLisible).join(', ')
  return JSON.stringify(v)
}

/** « champ : valeur · champ : valeur », ou « — » s'il n'y a rien. */
export function changementsLisibles(objet: Readonly<Record<string, unknown>> | null | undefined): string {
  if (!objet) return ''
  const morceaux = Object.entries(objet).map(([cle, v]) => `${cle.replace(/_/g, ' ')} : ${valeurLisible(v)}`)
  return morceaux.join(' · ')
}
