/**
 * Ce que partagent les écrans de l'atelier : lectures communes (magasins, métiers, motifs), nom
 * d'un métier « CODE · Nom » (an. 20, un seul nom partout), magasin par défaut, date lisible
 * (« 08/10/2026 (hier) »), inventaires qui suspendent une matière (périmètre, (b)).
 */
import { useEffect, useState } from 'react'

import { ErreurApi } from '../../lib/api'
import { date, kgTelephone } from '../../lib/format'
import { ajouterJours, aujourdhui, jourDansN } from '../../lib/heure'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { InventaireOuvert } from '../../lib/types-coque'
import type { MagasinFiche, MetierFiche, Motifs } from './types'

/** « M1 · Van de Wiele n° 1 », ou le code seul sans nom. */
export function nomMetier(m: { code: string; nom?: string | null }): string {
  return m.nom ? `${m.code} · ${m.nom}` : m.code
}

export const useMagasins = () => useLecture<MagasinFiche[]>('/magasins')
export const useMetiers = () => useLecture<MetierFiche[]>('/metiers')
export const useMotifs = () => useLecture<Motifs>('/motifs')

/** Le nom « CODE · Nom » d'un métier par son identifiant ; à défaut, le texte du serveur. */
export function useNomMetier(): (id: number | null | undefined, repli?: string) => string {
  const metiers = useMetiers()
  return (id, repli = '') => {
    const m = metiers.data?.find((x) => x.id === id)
    return m ? nomMetier(m) : repli
  }
}

export const estQuarantaine = (m: Pick<MagasinFiche, 'type'>) => m.type === 'quarantaine'

/** Les magasins d'où la matière peut partir : actifs, hors quarantaine. */
export function magasinsCourants(magasins: readonly MagasinFiche[] | undefined): MagasinFiche[] {
  return (magasins ?? []).filter((m) => m.actif && !estQuarantaine(m))
}

/** Le magasin proposé d'office : le courant le plus garni. */
export function magasinParDefaut(magasins: readonly MagasinFiche[] | undefined): number | null {
  const tries = [...magasinsCourants(magasins)].sort((a, b) => b.kg_detenus - a.kg_detenus)
  return tries[0]?.id ?? null
}

/** « 08/10/2026 (aujourd'hui) », « 07/10/2026 (hier) », sinon la date seule. */
export function dateLisible(jour: string): string {
  if (jour === aujourdhui()) return `${date(jour)} (aujourd’hui)`
  if (jour === jourDansN(-1)) return `${date(jour)} (hier)`
  return date(jour)
}

/** Un refus « introuvable » (404), distinct d'une coupure du réseau. */
export function estIntrouvable(e: unknown): boolean {
  return e instanceof ErreurApi && e.statut === 404
}

/** Un refus de version périmée (409 `conflit_version`). */
export function estConflitVersion(e: unknown): boolean {
  return e instanceof ErreurApi && e.statut === 409 && e.code === 'conflit_version'
}

/**
 * Les inventaires ouverts qui comptent l'une de ces matières dans ce magasin (ou dans tous) :
 * leurs mouvements y sont suspendus (b). `magasins` : les noms des magasins touchés.
 */
export function suspensions(
  inventaires: readonly InventaireOuvert[],
  matieres: readonly { id: number; reference: string }[],
  magasins: readonly string[],
): string[] {
  const textes: string[] = []
  for (const inv of inventaires) {
    if (inv.magasin && !magasins.includes(inv.magasin)) continue
    const comptee = matieres.find((m) => inv.matieres.includes(m.id))
    if (!comptee) continue
    textes.push(
      `L’inventaire ${inv.numero} (${inv.magasin ?? 'tous les magasins'}, du ${date(inv.date)}) compte ` +
        `« ${comptee.reference} » : ses mouvements y sont suspendus jusqu’à sa validation. ` +
        'Garder en brouillon, ou attendre.',
    )
  }
  return textes
}

/** Les phrases sans doublon, dans l'ordre. */
export const sansDoublon = (textes: readonly string[]) => [...new Set(textes.filter(Boolean))]

/** « 12,5 kg » au téléphone, « — » sinon. */
export const qte = kgTelephone

/** Les bornes d'une date de mouvement : après la période close, au plus tard aujourd'hui. */
export function useBornesDate(): { min?: string; raisonMin?: string } {
  const { contexte } = useSession()
  const close = contexte.date_cloture
  return close
    ? { min: ajouterJours(close, 1), raisonMin: `la période est close jusqu’au ${date(close)}` }
    : {}
}

/** La valeur, une fois la frappe posée `delai` ms (la recherche part 250 ms après la dernière touche). */
export function useDiffere<T>(valeur: T, delai = 250): T {
  const [differe, setDiffere] = useState(valeur)
  useEffect(() => {
    const t = setTimeout(() => setDiffere(valeur), delai)
    return () => clearTimeout(t)
  }, [valeur, delai])
  return differe
}
