/**
 * L'ouverture d'un inventaire, sans écran (ECRANS-PRO partie 6, « Ouvrir un inventaire ») :
 * libellé selon le périmètre et le magasin (an. 16), ce qui manque pour ouvrir, le conflit avec un
 * inventaire déjà ouvert (un par magasin ; un inventaire de tous les magasins exclut tout autre —
 * décision du lot D5, messages du serveur), les lots qui seront figés, la question, le corps de
 * `POST inventaires`.
 */
import { messageDate } from '../../composants/saisie/DateChamp'
import { nombre } from '../../lib/format'
import type { InventaireOuvert } from '../../lib/types-coque'
import type { LotSolde, MatiereResume } from './types'

export type Perimetre = 'tout' | 'famille' | 'matieres' | 'tournant'

export const PERIMETRES: readonly { valeur: Perimetre; libelle: string }[] = [
  { valeur: 'tout', libelle: 'Tout le stock' },
  { valeur: 'famille', libelle: 'Par rôle, composition ou classe ABC' },
  { valeur: 'matieres', libelle: 'Certaines matières' },
  { valeur: 'tournant', libelle: 'Inventaire tournant (matières dues)' },
]

export interface SaisieOuverture {
  libelle: string
  date: string
  /** `null` : tous les magasins. */
  magasin: number | null
  /** En pour cent (2 = 2 %). */
  tolerance: number | null
  perimetre: Perimetre
  roles: readonly number[]
  compositions: readonly number[]
  classes: readonly string[]
  matieres: readonly number[]
  /** Les matières dues que l'on a décochées (tournant). */
  ecartees: readonly number[]
}

/** Le libellé proposé quand on n'en écrit pas (an. 16). */
export function libelleAuto(s: SaisieOuverture, code: string | null, famille: string): string {
  const ou = code ? ` — ${code}` : ''
  switch (s.perimetre) {
    case 'famille':
      return `Inventaire par famille (${famille || 'aucun critère'})${ou}`
    case 'matieres':
      return `Inventaire de ${nombre(s.matieres.length)} matière(s)${ou}`
    case 'tournant':
      return `Inventaire tournant${ou}`
    default:
      return `Inventaire de tout le stock${code ? ` ${code}` : ''}`
  }
}

/** L'inventaire déjà ouvert qui empêche celui-ci (même magasin, ou l'un des deux sur tous). */
export function conflitOuvert(
  ouverts: readonly InventaireOuvert[],
  code: string | null,
): InventaireOuvert | null {
  return (
    ouverts.find((o) => o.magasin == null) ??
    (code == null ? ouverts[0] : ouverts.find((o) => o.magasin === code)) ??
    null
  )
}

/** Le refus que dirait le serveur (lot D5, C-07), suivi de ce qu'il faut faire. */
export function messageConflit(o: InventaireOuvert, code: string | null): string {
  const sur = o.magasin == null ? 'sur tous les magasins' : `sur « ${o.magasin} »`
  const suite =
    code == null && o.magasin != null
      ? ' : un inventaire de tous les magasins attend qu’il soit validé ou abandonné.'
      : '.'
  return `L’inventaire ${o.numero} est déjà ouvert ${sur}${suite} Le valider ou l’abandonner d’abord.`
}

/** Les matières retenues, si on peut les dire avant l'ouverture (`null` : toutes ; la classe ABC se calcule à l'ouverture). */
export function matieresRetenues(
  s: SaisieOuverture,
  matieres: readonly MatiereResume[],
  dues: readonly number[],
): Set<number> | null {
  if (s.perimetre === 'tout') return null
  if (s.perimetre === 'matieres') return new Set(s.matieres)
  if (s.perimetre === 'tournant') return new Set(dues.filter((d) => !s.ecartees.includes(d)))
  return new Set(
    matieres
      .filter((m) => !s.roles.length || (m.role_id != null && s.roles.includes(m.role_id)))
      .filter(
        (m) =>
          !s.compositions.length || (m.composition_id != null && s.compositions.includes(m.composition_id)),
      )
      .map((m) => m.id),
  )
}

/** Le nombre de soldes lot × magasin > 0 qui seront figés. */
export function lotsFiges(
  lots: readonly LotSolde[],
  magasin: number | null,
  retenues: Set<number> | null,
): number {
  let n = 0
  for (const l of lots) {
    if (retenues && !retenues.has(l.matiere_id)) continue
    for (const g of l.magasins) if (g.quantite > 0 && (magasin == null || g.magasin_id === magasin)) n += 1
  }
  return n
}

/** Ce qui manque pour ouvrir (raison du bouton, qui suit l'état). */
export function manqueOuverture(s: SaisieOuverture, min?: string, max?: string): string[] {
  const manque: string[] = []
  if (!s.date || messageDate(s.date, min, max)) manque.push('la date')
  if (s.tolerance == null || s.tolerance < 0 || s.tolerance > 100) manque.push('la tolérance (0 à 100 %)')
  if (s.perimetre === 'famille' && !s.roles.length && !s.compositions.length && !s.classes.length)
    manque.push('au moins un critère coché')
  if (s.perimetre === 'matieres' && !s.matieres.length) manque.push('au moins une matière')
  return manque
}

/** La question de la confirmation (an. 16 : selon le périmètre et le nombre de lots). */
export function questionOuverture(n: number | null, code: string | null): string {
  const ou = code ? `du magasin ${code}` : 'de tous les magasins'
  const quoi = n == null ? 'les lots des matières retenues' : `${nombre(n)} lot(s)`
  return `Figer ${quoi} ${ou} et suspendre leurs mouvements ?`
}

/** Le corps de `POST inventaires`. */
export function corpsOuverture(s: SaisieOuverture, libelle: string, dues: readonly number[]) {
  const criteres = {
    matieres:
      s.perimetre === 'matieres'
        ? [...s.matieres]
        : s.perimetre === 'tournant'
          ? dues.filter((d) => !s.ecartees.includes(d))
          : [],
    roles: s.perimetre === 'famille' ? [...s.roles] : [],
    compositions: s.perimetre === 'famille' ? [...s.compositions] : [],
    classes_abc: s.perimetre === 'famille' ? [...s.classes] : [],
  }
  return {
    date: s.date,
    magasin_id: s.magasin,
    libelle: (s.libelle.trim() || libelle).slice(0, 120),
    tolerance: (s.tolerance ?? 0) / 100,
    criteres,
  }
}
