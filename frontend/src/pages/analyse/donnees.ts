/**
 * Les lectures de l'Analyse, une clé par route (cache partagé entre la page, qui compte les
 * lignes de ses onglets, et les onglets eux-mêmes ; ECRANS-PRO P8-26). Le résultat précédent
 * reste affiché pendant qu'une nouvelle date ou de nouveaux critères se relisent.
 */
import { keepPreviousData } from '@tanstack/react-query'

import { useLecture } from '../../lib/requetes'
import type {
  ConsommationOrdre,
  Controles,
  ControleSoldes,
  Echeancier,
  HistoriquePrix,
  MatricePrix,
  Opportunites,
  PerformanceFournisseurs,
  Valorisation,
} from './types'

const GARDER = { placeholderData: keepPreviousData } as const

export const useValorisation = (date: string) =>
  useLecture<Valorisation>('/valorisation', date ? { date } : undefined, GARDER)

export const useHistoriquePrix = () => useLecture<HistoriquePrix>('/prix/historique')

export const useMatrice = () => useLecture<MatricePrix>('/prix/matrice')

/** Les critères des opportunités : ceux de l'écran (cases et fenêtre), vides = défauts du serveur. */
export interface CriteresOpportunites {
  meme_couleur: boolean
  autre_fournisseur: boolean
  prix_catalogue: boolean
  fenetre_jours: number | null
}

export const CRITERES_DEFAUT: CriteresOpportunites = {
  meme_couleur: true,
  autre_fournisseur: true,
  prix_catalogue: false,
  fenetre_jours: null,
}

/** Les paramètres d'adresse des opportunités : un « non » s'écrit (`qs` saute `false`). */
export const parametresOpportunites = (c: CriteresOpportunites) => ({
  meme_couleur: String(c.meme_couleur),
  autre_fournisseur: String(c.autre_fournisseur),
  prix_catalogue: String(c.prix_catalogue),
  fenetre_jours: c.fenetre_jours ?? undefined,
})

export const useOpportunites = (c: CriteresOpportunites = CRITERES_DEFAUT) =>
  useLecture<Opportunites>('/opportunites', parametresOpportunites(c), GARDER)

export const usePerformance = () => useLecture<PerformanceFournisseurs>('/fournisseurs/performance')

export const useControles = () => useLecture<Controles>('/controles')

export const useSoldes = () => useLecture<ControleSoldes>('/controles/soldes')

export interface FiltresEcheancier {
  q: string
  nature: string
  du: string
  au: string
}

export const useEcheancier = (f: FiltresEcheancier) =>
  useLecture<Echeancier>(
    '/echeancier',
    {
      q: f.q.trim() || undefined,
      nature: f.nature || undefined,
      du: f.du || undefined,
      au: f.au || undefined,
    },
    GARDER,
  )

export const useConsommation = () => useLecture<ConsommationOrdre[]>('/ordres/consommation')
