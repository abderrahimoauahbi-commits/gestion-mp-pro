/**
 * La saisie d'une sortie vers les machines au téléphone (`/atelier/envoyer`) : la demande, les
 * lots, l'enregistrement. Toute la saisie est gardée sur le téléphone (`useSaisieGardee`, an. 17)
 * jusqu'à l'enregistrement ou l'abandon ; un brouillon rouvert garde la sienne sous son numéro
 * et sa version. Les disponibles sont lus **à la date de l'ordre** (an. 23).
 */
import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { saisieGardee, useSaisieGardee } from '../../composants/atelier/saisieGardee'
import { api, messageErreur } from '../../lib/api'
import { aujourdhui } from '../../lib/heure'
import { useLecture } from '../../lib/requetes'
import { magasinParDefaut, useMagasins } from './commun'
import {
  depasse,
  kgDe,
  lignesDuCorps,
  priseDe,
  priseRouverte,
  qualitesDuCorps,
  regrouper,
  type Fabrication,
  type Prise,
} from './sortie'
import type { LigneProposee, LotSolde, OrdreFiche, Proposition } from './types'

export interface EtatSortie {
  id: number | null
  version: number | null
  jour: string
  magasin: number | null
  metier: number | null
  commentaire: string
  horsRecette: boolean
  fabrications: Fabrication[]
  besoins: LigneProposee[]
  incompletes: string[]
  blocagesServeur: string[]
  prises: Prise[]
  etape: 'demande' | 'lots'
  demandeChangee: boolean
  /** Le prévu d'un brouillon rouvert a été relu (proposition à sa date). */
  besoinsRelus: boolean
}

export function etatInitial(ordre: OrdreFiche | null): EtatSortie {
  return {
    id: ordre?.id ?? null,
    version: ordre?.version ?? null,
    jour: ordre?.date ?? aujourdhui(),
    magasin: ordre?.magasin_id ?? null,
    metier: ordre?.metier_id ?? null,
    commentaire: ordre?.commentaire ?? '',
    horsRecette: ordre ? !ordre.qualites.length : false,
    fabrications: ordre?.qualites.length
      ? ordre.qualites.map((q) => ({ qualite: q.qualite_id, m2: q.m2 }))
      : [{ qualite: null, m2: 0 }],
    besoins: [],
    incompletes: [],
    blocagesServeur: [],
    prises: (ordre?.lignes ?? []).map(priseRouverte),
    etape: ordre ? 'lots' : 'demande',
    demandeChangee: false,
    besoinsRelus: !ordre?.qualites.length,
  }
}

export const cleSaisie = (ordre: OrdreFiche | null) =>
  ordre ? `envoyer:${ordre.id}:v${ordre.version}` : 'envoyer'

/** Le brouillon rouvert relit ce que demandent ses recettes, à sa date, sans toucher ses prises. */
function useBesoinsRelus(e: EtatSortie, magasin: number | null, poser: (m: Partial<EtatSortie>) => void) {
  const [erreur, setErreur] = useState('')
  useEffect(() => {
    if (e.besoinsRelus || magasin == null || e.horsRecette) return
    api
      .post<Proposition>('/ordres/proposition', {
        date: e.jour,
        magasin_id: magasin,
        qualites: qualitesDuCorps(false, e.fabrications),
      })
      .then((r) =>
        poser({
          besoins: r.lignes,
          incompletes: r.recettes_incompletes,
          blocagesServeur: r.blocages,
          besoinsRelus: true,
        }),
      )
      .catch((x: unknown) =>
        setErreur(
          `Le prévu par la recette n’a pas pu être relu (${messageErreur(x)}) : rouvrir ce brouillon.`,
        ),
      )
  }, [e.besoinsRelus, e.horsRecette, e.jour, e.fabrications, magasin, poser])
  return erreur
}

/** Ce que portent les lots et ce que donnent les prises : disponibles, fils, totaux, refus. */
function useCalculs(e: EtatSortie, magasin: number | null) {
  const soldes = useLecture<LotSolde[]>(e.etape === 'lots' && magasin != null ? '/lots' : null, {
    magasin,
    date: e.jour,
    non_nuls: true,
  })
  /** Ce que le lot porte, à la date de l'ordre, dans le magasin choisi ; −1 tant qu'on ne le sait pas. */
  const dispo = (p: Prise): number => {
    for (const b of e.besoins) {
      const l = b.disponibles.find((x) => x.lot_id === p.lot_id)
      if (l) return l.disponible
    }
    const x = soldes.data?.find((l) => l.lot_id === p.lot_id)
    if (x) return x.magasins.find((m) => m.magasin_id === magasin)?.quantite ?? 0
    return soldes.data ? 0 : -1
  }
  const fils = regrouper(e.besoins, e.prises)
  const aEnvoyer = e.prises.filter((p) => p.quantite > 0)
  return {
    dispo,
    fils,
    soldes: soldes.data ?? [],
    aEnvoyer,
    depassements: e.prises.filter((p) => depasse(p, dispo(p))),
    sansContenance: aEnvoyer.filter((p) => p.unite !== 'kg' && kgDe(p) === 0),
    totalPrevu: e.besoins.reduce((t, b) => t + b.prevu, 0),
    totalSorti: fils.reduce((t, f) => t + f.sorti, 0),
  }
}

/** La proposition du serveur : remplace les prises de recette, garde les fils ajoutés à la main. */
async function proposer(e: EtatSortie, magasin: number | null): Promise<Partial<EtatSortie>> {
  if (e.horsRecette)
    return { besoins: [], incompletes: [], blocagesServeur: [], etape: 'lots', demandeChangee: false }
  const r = await api.post<Proposition>('/ordres/proposition', {
    date: e.jour,
    magasin_id: magasin,
    metier_id: e.metier,
    qualites: qualitesDuCorps(false, e.fabrications),
  })
  const deRecette = new Set([...r.lignes, ...e.besoins].map((l) => l.matiere_id))
  const gardees = e.prises.filter((p) => !deRecette.has(p.matiere_id))
  const proposees = r.lignes.flatMap((l) => l.lots.map((lot) => priseDe(l, lot, lot.propose)))
  return {
    besoins: r.lignes,
    incompletes: r.recettes_incompletes,
    blocagesServeur: r.blocages,
    prises: [...proposees, ...gardees],
    etape: 'lots',
    demandeChangee: false,
    besoinsRelus: true,
  }
}

/**
 * Enregistre le brouillon (créé ou modifié), puis le valide si demandé. Un refus à la
 * validation laisse le brouillon enregistré, et le dit.
 */
async function enregistrerOrdre(
  e: EtatSortie,
  magasin: number | null,
  valider: boolean,
  garde: (fiche: OrdreFiche) => void,
): Promise<OrdreFiche> {
  const corps = {
    date: e.jour,
    magasin_id: magasin,
    metier_id: e.metier,
    commentaire: e.commentaire.trim(),
    qualites: qualitesDuCorps(e.horsRecette, e.fabrications),
    lignes: lignesDuCorps(e.prises),
  }
  const fiche =
    e.id != null
      ? await api.put<OrdreFiche>(`/ordres/${e.id}`, { ...corps, version: e.version })
      : await api.post<OrdreFiche>('/ordres', corps)
  if (!valider) return fiche
  try {
    return await api.post<OrdreFiche>(`/ordres/${fiche.id}/valider`, { version: fiche.version })
  } catch (x) {
    garde(fiche)
    throw new Error(`${messageErreur(x)} — l’ordre est gardé en brouillon, modifiable.`, { cause: x })
  }
}

export function useSaisieSortie(ordre: OrdreFiche | null) {
  const cle = cleSaisie(ordre)
  const [repris] = useState(() => !ordre && saisieGardee(cle))
  const [e, setE, oublier] = useSaisieGardee<EtatSortie>(cle, etatInitial(ordre))
  const [erreur, setErreur] = useState('')
  const client = useQueryClient()
  const magasins = useMagasins()
  const magasin = e.magasin ?? magasinParDefaut(magasins.data)
  const poser = useMemo(() => (m: Partial<EtatSortie>) => setE((avant) => ({ ...avant, ...m })), [setE])
  const erreurRelecture = useBesoinsRelus(e, magasin, poser)
  const calculs = useCalculs(e, magasin)
  return {
    e,
    poser,
    changerDemande: (m: Partial<EtatSortie>) => poser({ ...m, demandeChangee: true }),
    magasin,
    repris,
    ...calculs,
    proposer: async () => {
      setErreur('')
      try {
        poser(await proposer(e, magasin))
      } catch (x) {
        setErreur(messageErreur(x))
      }
    },
    /** Enregistré : la saisie gardée est oubliée (aucune écriture de l'état ne suit). */
    enregistrer: async (valider: boolean): Promise<OrdreFiche | undefined> => {
      setErreur('')
      try {
        const fiche = await enregistrerOrdre(e, magasin, valider, (f) =>
          poser({ id: f.id, version: f.version }),
        )
        oublier()
        return fiche
      } catch (x) {
        setErreur(messageErreur(x))
        return undefined
      } finally {
        void client.invalidateQueries()
      }
    },
    abandonner: oublier,
    erreur: erreur || erreurRelecture,
  }
}

export type SaisieSortie = ReturnType<typeof useSaisieSortie>
