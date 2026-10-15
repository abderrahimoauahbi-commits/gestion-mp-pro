/**
 * L'état de la saisie d'un ordre (nouveau, ou brouillon rouvert) et ses gestes : proposer,
 * corriger une prise, ajouter un lot, garder en brouillon, valider. Les règles sont dans le moteur
 * unique `lib/ordre.ts` (le même que le téléphone).
 * Un brouillon rouvert relit le prévu de ses recettes à sa date sans toucher à ses prises ; une
 * prise reprend l'unité où elle a sans doute été saisie (bobines quand le compte tombe juste).
 */
import { useEffect, useMemo, useState } from 'react'

import { useDernierOrdre } from '../../lib/dernierOrdre'
import { aujourdhui } from '../../lib/heure'
import {
  blocagesSaisie,
  corpsOrdre,
  demanderProposition,
  enregistrerOrdre,
  filsDe,
  manqueBrouillon,
  manqueProposer,
  nouvelleCle,
  priseRouverte,
  recalculer,
  type CorpsOrdre,
  type Fabrication,
  type Prise,
} from '../../lib/ordre'
import { useEcriture, useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Unite } from '../../lib/unites'
import type { LotSolde, Magasin } from '../stock/types'
import { estQuarantaine } from '../stock/types'
import { type LigneProposee, type OrdreFiche } from './donnees'

/** Le magasin proposé d'abord : le plus garni des magasins courants actifs. */
function magasinParDefaut(magasins: readonly Magasin[] | undefined): number | null {
  const courants = (magasins ?? []).filter((g) => g.actif && !estQuarantaine(g.type))
  return [...courants].sort((a, b) => b.kg_detenus - a.kg_detenus)[0]?.id ?? null
}

function useDemande(fiche: OrdreFiche | null) {
  const [jour, setJour] = useState(fiche?.date ?? aujourdhui())
  const [magasin, setMagasin] = useState<number | null>(fiche?.magasin_id ?? null)
  const [metier, setMetier] = useState<number | null>(fiche?.metier_id ?? null)
  const [commentaire, setCommentaire] = useState(fiche?.commentaire ?? '')
  const [horsRecette, setHorsRecette] = useState(fiche ? !fiche.qualites.length : false)
  const [fabrications, setFabrications] = useState<Fabrication[]>(
    fiche?.qualites.length
      ? fiche.qualites.map((q) => ({ qualite_id: q.qualite_id, m2: q.m2 }))
      : [{ qualite_id: null, m2: null }],
  )
  return {
    jour,
    setJour,
    magasin,
    setMagasin,
    metier,
    setMetier,
    commentaire,
    setCommentaire,
    horsRecette,
    setHorsRecette,
    fabrications,
    setFabrications,
  }
}

type Demande = ReturnType<typeof useDemande>

export { corpsOrdre, type CorpsOrdre }

/** Le magasin choisi (le plus garni d'abord) et le disponible de ses lots **à la date de l'ordre**. */
function useMagasin(d: Demande) {
  const magasins = useLecture<Magasin[]>('/magasins')
  const magasinChoisi = d.magasin ?? magasinParDefaut(magasins.data)
  const lots = useLecture<LotSolde[]>(magasinChoisi && d.jour ? '/lots' : null, {
    magasin: magasinChoisi,
    date: d.jour,
  })
  const dispo = useMemo(() => {
    if (!lots.data) return null
    const m = new Map<number, number>()
    for (const l of lots.data)
      m.set(l.lot_id, l.magasins.find((g) => g.magasin_id === magasinChoisi)?.quantite ?? 0)
    return m
  }, [lots.data, magasinChoisi])
  return {
    magasinChoisi,
    magasins: (magasins.data ?? []).filter((g) => g.actif && !estQuarantaine(g.type)),
    magasinCode: magasins.data?.find((g) => g.id === magasinChoisi)?.code ?? '',
    magasinNom: magasins.data?.find((g) => g.id === magasinChoisi)?.nom ?? '',
    lotsDuMagasin: lots.data ?? [],
    dispo,
  }
}

/** La proposition du serveur ; un brouillon rouvert relit le prévu de ses recettes à sa date. */
function useProposition(fiche: OrdreFiche | null, magasin: number | null, jour: string) {
  const [besoins, setBesoins] = useState<LigneProposee[]>([])
  const [incompletes, setIncompletes] = useState<string[]>([])
  const proposition = useEcriture(
    ({
      demande,
      magasin: m,
    }: {
      demande: Parameters<typeof demanderProposition>[0]
      magasin: number | null
    }) => demanderProposition(demande, m),
    { invalider: false },
  )
  const [relu, setRelu] = useState(!fiche?.qualites.length)
  useEffect(() => {
    if (relu || !fiche || !magasin) return
    setRelu(true)
    const fabrications = fiche.qualites.map((q) => ({ qualite_id: q.qualite_id, m2: q.m2 }))
    const demande = { jour, metier: null, commentaire: '', horsRecette: false, fabrications }
    proposition
      .mutateAsync({ demande, magasin })
      .then((r) => {
        setBesoins(r.lignes)
        setIncompletes(r.recettes_incompletes)
      })
      .catch(() => undefined)
  }, [relu, fiche, magasin, jour, proposition])
  return { besoins, setBesoins, incompletes, setIncompletes, proposition }
}

/** Garder en brouillon (créé ou modifié), puis valider si demandé ; un refus le laisse en brouillon. */
function useEnregistrer(fiche: OrdreFiche | null, corps: () => CorpsOrdre, setSale: (v: boolean) => void) {
  const [cible, setCible] = useState(fiche ? { id: fiche.id, version: fiche.version } : null)
  const ecrire = useEcriture(({ valider }: { valider: boolean }) =>
    enregistrerOrdre(cible, corps(), valider, (b) => {
      setCible({ id: b.id, version: b.version })
      setSale(false)
    }),
  )
  return { cible, enregistrer: (valider: boolean) => ecrire.mutateAsync({ valider }) }
}

/** Les prises et leurs gestes ; toute retouche rend la saisie « sale ». */
function usePrises(fiche: OrdreFiche | null, toucher: () => void) {
  const [prises, setPrises] = useState<Prise[]>(() => (fiche?.lignes ?? []).map(priseRouverte))
  return {
    prises,
    setPrises,
    changerKg: (cle: string, kg: number | null) => {
      setPrises((t) => t.map((p) => (p.cle === cle ? { ...p, kg } : p)))
      toucher()
    },
    changerUnite: (cle: string, unite: Unite) =>
      setPrises((t) => t.map((p) => (p.cle === cle ? { ...p, unite } : p))),
    retirer: (cle: string) => {
      setPrises((t) => t.filter((p) => p.cle !== cle))
      toucher()
    },
    ajouter: (p: Omit<Prise, 'cle'>) => {
      setPrises((t) => (t.some((x) => x.lot_id === p.lot_id) ? t : [...t, { ...p, cle: nouvelleCle() }]))
      toucher()
    },
  }
}

/** Les gestes de la demande : chacun marque la saisie, et la demande changée appelle « Recalculer ». */
function gestesDemande(d: Demande, toucher: () => void, changer: (f: () => void) => void, vider: () => void) {
  return {
    setJour: (v: string) => changer(() => d.setJour(v)),
    setMagasin: (v: number | null) =>
      changer(() => {
        d.setMagasin(v)
        vider()
      }),
    setMetier: (v: number | null) => {
      d.setMetier(v)
      toucher()
    },
    setCommentaire: (v: string) => {
      d.setCommentaire(v)
      toucher()
    },
    setHorsRecette: (v: boolean) => changer(() => d.setHorsRecette(v)),
    setFabrication: (i: number, modif: Partial<Fabrication>) =>
      changer(() => d.setFabrications((t) => t.map((x, j) => (j === i ? { ...x, ...modif } : x)))),
    ajouterFabrication: () => changer(() => d.setFabrications((t) => [...t, { qualite_id: null, m2: null }])),
    retirerFabrication: (i: number) => changer(() => d.setFabrications((t) => t.filter((_, j) => j !== i))),
  }
}

export function useSaisieOrdre(fiche: OrdreFiche | null) {
  const { contexte } = useSession()
  const d = useDemande(fiche)
  const m = useMagasin(d)
  const [sale, setSale] = useState(false)
  const [demandeChangee, setDemandeChangee] = useState(false)
  const toucher = () => setSale(true)
  const p = usePrises(fiche, toucher)
  const pr = useProposition(fiche, m.magasinChoisi, d.jour)
  const e = useEnregistrer(fiche, () => corpsOrdre(d, m.magasinChoisi, p.prises), setSale)
  const dernier = useDernierOrdre(e.cible?.id ?? fiche?.id)
  const changer = (f: () => void) => {
    f()
    setDemandeChangee(true)
    toucher()
  }
  const proposer = async () => {
    const r = await pr.proposition.mutateAsync({ demande: d, magasin: m.magasinChoisi })
    p.setPrises((avant) => recalculer(avant, pr.besoins, r.lignes))
    pr.setBesoins(r.lignes)
    pr.setIncompletes(r.recettes_incompletes)
    setDemandeChangee(false)
    toucher()
  }
  const blocages = blocagesSaisie(p.prises, {
    jour: d.jour,
    aujourdhui: aujourdhui(),
    cloture: contexte.date_cloture,
    dernier,
    magasin: { code: m.magasinCode, nom: m.magasinNom },
    inventaires: contexte.inventaires_ouverts,
    dispo: m.dispo,
  })
  return {
    ...d,
    ...m,
    ...p,
    ...gestesDemande(d, toucher, changer, () => {
      p.setPrises([])
      pr.setBesoins([])
    }),
    besoins: pr.besoins,
    incompletes: pr.incompletes,
    fils: filsDe(pr.besoins, p.prises),
    demandeChangee,
    sale,
    blocages,
    manqueProposer: manqueProposer({
      jour: d.jour,
      magasin: m.magasinChoisi,
      horsRecette: d.horsRecette,
      fabrications: d.fabrications,
    }),
    manqueBrouillon: manqueBrouillon(p.prises),
    proposer,
    proposeEnCours: pr.proposition.isPending,
    ...e,
  }
}

export type SaisieOrdre = ReturnType<typeof useSaisieOrdre>
