/**
 * Les règles d'un déplacement de lot à l'atelier (transfert, ECRANS-PRO partie 3, (d)) : départ
 * hors quarantaine, le plus garni d'abord ; arrivée active, autre que le départ ; vers une
 * quarantaine, motif imposé « Mise en quarantaine » et observations obligatoires (≥ 3) ; la
 * libération de quarantaine n'est pas un geste de l'atelier.
 */
import { aujourdhui } from '../../lib/heure'
import type { Unite } from '../../lib/unites'
import type { LotFiche, MagasinFiche, MotifLu } from './types'

export interface SaisieDeplacement {
  depuis: number | null
  vers: number | null
  /** `null` : tout ce qui est dans le magasin de départ (relu après chaque déplacement). */
  kg: number | null
  unite: Unite
  motif: number | null
  jour: string
  commentaire: string
}

export const deplacementVide = (): SaisieDeplacement => ({
  depuis: null,
  vers: null,
  kg: null,
  unite: 'kg',
  motif: null,
  jour: aujourdhui(),
  commentaire: '',
})

export const MISE_EN_QUARANTAINE = 'Mise en quarantaine'

/** Les magasins de départ : hors quarantaine, avec de la matière, le plus garni d'abord. */
export function departs(lot: LotFiche) {
  return lot.magasins
    .filter((m) => m.type !== 'quarantaine' && m.quantite > 0.0005)
    .sort((a, b) => b.quantite - a.quantite)
}

/** Les magasins d'arrivée : actifs, autres que le départ ; la quarantaine dite comme telle. */
export function arrivees(magasins: readonly MagasinFiche[], depuis: number | null) {
  return magasins
    .filter((m) => m.actif && m.id !== depuis)
    .map((m) => ({
      id: m.id,
      titre: m.type === 'quarantaine' ? `${m.code} (quarantaine : matière douteuse)` : m.code,
      sous: m.nom === m.code ? undefined : m.nom,
    }))
}

/** Les motifs d'un transfert de l'atelier (sans la libération, ni la mise en quarantaine, imposée). */
export function motifsAtelier(motifs: readonly MotifLu[]): MotifLu[] {
  return motifs.filter((m) => m.type === 'transfert' && !m.impose_role && m.libelle !== MISE_EN_QUARANTAINE)
}

/** Le motif imposé vers une quarantaine. */
export const motifQuarantaine = (motifs: readonly MotifLu[]) =>
  motifs.find((m) => m.type === 'transfert' && m.libelle === MISE_EN_QUARANTAINE)

/** La raison de griser « Déplacer », dans l'ordre où on la lève. */
export function raisonDeplacer(e: {
  blocages: readonly string[]
  vers: number | null
  kg: number
  dispo: number
  quarantaine: boolean
  commentaire: string
}): string {
  if (e.blocages.length) return 'Un inventaire est en cours (voir le bandeau)'
  if (e.vers == null) return 'Choisir le magasin d’arrivée'
  if (!(e.kg > 0)) return 'Saisir la quantité'
  if (e.kg > e.dispo + 0.0005) return 'Plus que ce qui est là'
  if (e.quarantaine && e.commentaire.trim().length < 3)
    return 'Écrire ce qui est douteux, dans les observations'
  return ''
}

/** Ce que la saisie donne une fois lue contre le lot et les magasins. */
export function lireDeplacement(l: LotFiche, s: SaisieDeplacement, mags: readonly MagasinFiche[]) {
  const ds = departs(l)
  const depuis = s.depuis ?? ds[0]?.magasin_id ?? null
  const dispo = ds.find((m) => m.magasin_id === depuis)?.quantite ?? 0
  const vers = mags.find((m) => m.id === s.vers)
  const depart = mags.find((m) => m.id === depuis)
  return {
    ds,
    depuis,
    dispo,
    kg: s.kg ?? dispo,
    vers,
    depart,
    quarantaine: vers?.type === 'quarantaine',
  }
}
