/**
 * L'en-tête de la fenêtre de comptage (ECRANS-PRO partie 6) : le badge (« Comptage en cours »,
 * « Validé par {nom} », « Abandonné par {nom} », « Annulé par {nom} ») et la ligne « {magasin} ·
 * {périmètre} · compté le … · tolérance … · par {nom}[ · validé le … par …][ · annulé le … par … :
 * {motif}] ».
 */
import { date, horodatage, part } from '../../lib/format'
import { magasinDe, type InventaireFiche } from './types'

function badge(i: InventaireFiche, libelle: string): string {
  if (i.statut === 'valide') return `${libelle} par ${i.valide_par}`
  if (i.statut === 'abandonne') return `${libelle} par ${i.abandonne_par}`
  if (i.statut === 'annule') return `${libelle} par ${i.annule_par}`
  return libelle
}

function ligne(i: InventaireFiche): string {
  const morceaux = [
    magasinDe(i),
    i.perimetre,
    `compté le ${date(i.date)}`,
    `tolérance ${part(i.tolerance, 0)}`,
    `par ${i.cree_par}`,
  ]
  if (i.valide_le) morceaux.push(`validé le ${horodatage(i.valide_le)} par ${i.valide_par}`)
  if (i.abandonne_le)
    morceaux.push(
      `abandonné le ${horodatage(i.abandonne_le)} par ${i.abandonne_par}${i.abandon_motif ? ` : ${i.abandon_motif}` : ''}`,
    )
  if (i.annule_le)
    morceaux.push(
      `annulé le ${horodatage(i.annule_le)} par ${i.annule_par}${i.annulation_motif ? ` : ${i.annulation_motif}` : ''}`,
    )
  return morceaux.filter(Boolean).join(' · ')
}

export const enTeteDeFiche = { badge, ligne }
