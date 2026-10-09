/**
 * L'aide, une seule source : `aide.json` (A7). Le Mode d'emploi, le « ? » de chaque écran, les
 * formules des indicateurs (`Kpi`) et `docs/NOTICE.md` (`scripts/generer_notice.py`) la lisent.
 *
 * Les textes portent une petite écriture, la même que Markdown : `**gras**`, `*italique*`,
 * `[libellé](/chemin)` (un lien d'écran, filtré par rôle à l'affichage) et `{{sur_les_metiers}}`
 * (le texte unique « Sur les métiers », repris mot pour mot partout où le fil monté s'explique).
 *
 * Les types ci-dessous sont vérifiés par le compilateur contre le fichier : une section mal formée
 * ne passe pas `tsc`.
 */
import aide from '../aide.json'
import type { Role } from './types'

export interface AideEcran {
  titre: string
  resume: string
  points: readonly string[]
}

export interface Formule {
  grandeur: string
  texte: string
}

export interface Procedure {
  titre: string
  vers: string
  vers_par_role?: Partial<Record<Role, string>>
  etapes: readonly string[]
}

export interface ModeEmploi {
  titre: string
  sous_titre: string
  regles: { titre: string; elements: readonly { titre: string; texte: string }[] }
  roles: { titre: string; cartes: readonly { titre: string; role: string; points: readonly string[] }[] }
  pas: { titre: string; procedures: readonly Procedure[] }
  calculs: { titre: string; lignes: readonly string[]; pied: string }
  analyse: {
    titre: string
    note_permise: string
    note_reservee: string
    lignes: readonly { nom: string; onglet: string; texte: string }[]
  }
  ecrans: {
    titre: string
    pied: string
    lignes: readonly { erp: string; ou: string; vers: string; note: string }[]
  }
  telephone: { titre: string; etapes: readonly string[] }
}

export const AIDE_ECRANS: Readonly<Record<string, AideEcran>> = aide.ecran
export const FORMULES: Readonly<Record<string, Formule>> = aide.formule
export const MODE_EMPLOI: ModeEmploi = aide.mode_emploi

/** Les textes communs, repris par `{{cle}}`. */
const COMMUNS: Readonly<Record<string, string>> = { sur_les_metiers: aide.sur_les_metiers }

/** Le texte unique « Sur les métiers » (ECRANS-PRO partie 1). */
export const SUR_LES_METIERS = aide.sur_les_metiers

/** Remplace `{{cle}}` par le texte commun (une clé inconnue reste visible, l'essai la voit). */
export function developper(texte: string): string {
  return texte.replace(/\{\{(\w+)\}\}/g, (tout, cle: string) => COMMUNS[cle] ?? tout)
}

/** La formule d'un indicateur (`formule.<cle>`), pour `Kpi({formule})`. */
export function formule(cle: keyof typeof aide.formule): string {
  return developper(aide.formule[cle].texte)
}

export type Morceau =
  | { genre: 'texte'; texte: string }
  | { genre: 'gras'; texte: string }
  | { genre: 'italique'; texte: string }
  | { genre: 'lien'; texte: string; vers: string }

const MOTIF = /\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\(([^)\s]+)\)/g

/** Découpe un texte d'aide en morceaux (après `{{…}}`). */
export function morceaux(brut: string): Morceau[] {
  const texte = developper(brut)
  const sortie: Morceau[] = []
  let depuis = 0
  for (const m of texte.matchAll(MOTIF)) {
    const debut = m.index ?? 0
    if (debut > depuis) sortie.push({ genre: 'texte', texte: texte.slice(depuis, debut) })
    if (m[1] != null) sortie.push({ genre: 'gras', texte: m[1] })
    else if (m[2] != null) sortie.push({ genre: 'italique', texte: m[2] })
    else sortie.push({ genre: 'lien', texte: m[3] ?? '', vers: m[4] ?? '' })
    depuis = debut + m[0].length
  }
  if (depuis < texte.length) sortie.push({ genre: 'texte', texte: texte.slice(depuis) })
  return sortie
}

/** Tous les liens d'écran cités par l'aide (essai : chacun vise un écran déclaré). */
export function liensDeLAide(): string[] {
  const textes: string[] = [JSON.stringify(aide)]
  return textes.flatMap((t) => [...t.matchAll(/\]\((\/[^)\s"]*)\)/g)].map((m) => m[1] ?? ''))
}
