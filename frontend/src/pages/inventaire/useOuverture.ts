/**
 * Les lectures et les calculs de la fenêtre « Ouvrir un inventaire » : propositions du serveur
 * (tolérance, rôles, compositions), magasins, matières, lots en stock, matières dues du tournant ;
 * puis le libellé proposé, les matières en stock du magasin choisi (an. 17), les lots figés, le
 * conflit avec un inventaire ouvert, la borne de la période close.
 */
import { useMemo } from 'react'

import { ajouterJours } from '../../lib/heure'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { InventaireOuvert } from '../../lib/types-coque'
import {
  conflitOuvert,
  libelleAuto,
  lotsFiges,
  matieresRetenues,
  messageConflit,
  type SaisieOuverture,
} from './ouverture'
import type { DefautsInventaire, LotSolde, MagasinFiche, MatiereACompter, MatiereResume } from './types'

export function useDonneesOuverture(s: SaisieOuverture) {
  return {
    defauts: useLecture<DefautsInventaire>('/inventaires/defauts'),
    magasins: useLecture<MagasinFiche[]>('/magasins'),
    matieres: useLecture<MatiereResume[]>('/matieres'),
    lots: useLecture<LotSolde[]>('/lots', { non_nuls: true }),
    dues: useLecture<MatiereACompter[]>(s.perimetre === 'tournant' ? '/inventaires/a-compter' : null, {
      magasin: s.magasin ?? undefined,
    }),
  }
}

type Donnees = ReturnType<typeof useDonneesOuverture>

export interface CalculsOuverture {
  /** La saisie, la tolérance proposée par les réglages posée si on n'en a pas tapé. */
  saisie: SaisieOuverture
  magasins: MagasinFiche[]
  code: string | null
  libelle: string
  idsDues: number[]
  enStock: MatiereResume[]
  stockDe: (id: number) => number
  nbLots: number | null
  conflit: InventaireOuvert | null
  grise: string | undefined
  min: string | undefined
}

/** Les matières (et le stock de chacune) présentes dans le magasin choisi, ou partout. */
function useEnStock(lots: readonly LotSolde[], matieres: readonly MatiereResume[], magasin: number | null) {
  return useMemo(() => {
    const ici = (g: { magasin_id: number; quantite: number }) =>
      g.quantite > 0 && (magasin == null || g.magasin_id === magasin)
    const stock = new Map<number, number>()
    for (const l of lots)
      for (const g of l.magasins.filter(ici))
        stock.set(l.matiere_id, (stock.get(l.matiere_id) ?? 0) + g.quantite)
    return { enStock: matieres.filter((m) => stock.has(m.id)), stockDe: (id: number) => stock.get(id) ?? 0 }
  }, [lots, matieres, magasin])
}

/** Le texte des critères d'une famille (« Poil, classe A »). */
function texteFamille(s: SaisieOuverture, defauts: DefautsInventaire | undefined): string {
  return [
    ...(defauts?.roles ?? []).filter((r) => s.roles.includes(r.id)).map((r) => r.code),
    ...(defauts?.compositions ?? []).filter((c) => s.compositions.includes(c.id)).map((c) => c.code),
    ...s.classes.map((c) => `classe ${c}`),
  ].join(', ')
}

export function useCalculsOuverture(s: SaisieOuverture, d: Donnees): CalculsOuverture {
  const { contexte } = useSession()
  const proposee = d.defauts.data ? Math.round(d.defauts.data.tolerance * 10000) / 100 : null
  const saisie = { ...s, tolerance: s.tolerance ?? proposee }
  const magasins = (d.magasins.data ?? []).filter((g) => g.actif)
  const code = magasins.find((g) => g.id === s.magasin)?.code ?? null
  const lots = d.lots.data ?? []
  const idsDues = (d.dues.data ?? []).map((x) => x.article_id)
  const retenues = matieresRetenues(saisie, d.matieres.data ?? [], idsDues)
  const { enStock, stockDe } = useEnStock(lots, d.matieres.data ?? [], s.magasin)
  const conflit = conflitOuvert(contexte.inventaires_ouverts, code)
  const aucuneDue = s.perimetre === 'tournant' && Boolean(d.dues.data) && retenues?.size === 0
  return {
    saisie,
    magasins,
    code,
    libelle: libelleAuto(saisie, code, texteFamille(s, d.defauts.data)),
    idsDues,
    enStock,
    stockDe,
    nbLots: s.perimetre === 'famille' && s.classes.length ? null : lotsFiges(lots, s.magasin, retenues),
    conflit,
    grise: conflit ? messageConflit(conflit, code) : aucuneDue ? 'Aucune matière due retenue.' : undefined,
    min: contexte.date_cloture ? ajouterJours(contexte.date_cloture, 1) : undefined,
  }
}
