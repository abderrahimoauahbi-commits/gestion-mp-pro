/**
 * L'état de la saisie d'un camion : l'en-tête, les factures par devise, les lignes, et les gestes
 * qui effaceraient une saisie (changer de fournisseur, décocher un bon ou une référence, retirer une
 * ligne pesée),
 * qui demandent d'abord (`question`). Un nouveau camion part de la date du jour ; un brouillon à
 * corriger part de sa fiche.
 */
import { useMemo, useState, type ReactNode } from 'react'

import { ajouterJours, aujourdhui } from '../../lib/heure'
import type { CommandeFiche, CommandeResume } from '../commandes/types'
import type { Matiere } from '../plan-achat/types'
import {
  depuisFiche,
  estSaisie,
  ligneDuBon,
  ligneHorsCommande,
  nouvelleCle,
  type FactureSaisie,
  type LigneSaisie,
} from './calculSaisie'
import type { Fournisseur, Magasin, ReceptionFiche } from './types'

export interface Question {
  texte: ReactNode
  oui: string
  faire: () => void
}

const FACTURE_VIDE: FactureSaisie = { numero: '', date: '', montant: null, echeance: '' }

const OUVERTS = new Set(['envoyee', 'confirmee', 'a_approuver'])

/** Un bon qui attend sa livraison : parti (numéroté), pas clos, du reste à livrer. */
export const bonOuvert = (c: CommandeResume) => Boolean(c.numero) && OUVERTS.has(c.statut) && c.reste_kg > 0

function facturesDe(r: ReceptionFiche | null): Record<string, FactureSaisie> {
  if (!r?.facture) return {}
  const f = r.facture
  return {
    [r.devise]: { numero: f.numero, date: f.date ?? '', montant: f.montant, echeance: f.echeance ?? '' },
  }
}

export interface Referentiels {
  fournisseurs: readonly Fournisseur[]
  bons: readonly CommandeResume[]
  matieres: readonly Matiere[]
  magasins: readonly Magasin[]
}

/** L'en-tête et les factures par devise (l'échéance suit la date tant qu'on ne l'a pas saisie). */
function useEnTete(r: ReceptionFiche | null, fournisseur: Fournisseur | null, marquer: () => void) {
  const [entete, setEntete] = useState({
    date: r?.date ?? aujourdhui(),
    numeroBl: r?.numero_bl ?? '',
    controlePar: r?.controle_par ?? '',
    observations: r?.observations ?? '',
  })
  const [factures, setFactures] = useState<Record<string, FactureSaisie>>(() => facturesDe(r))
  const [saisies, setSaisies] = useState<Record<string, boolean>>(() =>
    r?.facture?.echeance ? { [r.devise]: true } : {},
  )
  return {
    entete,
    poserEntete: (m: Partial<typeof entete>) => {
      marquer()
      setEntete((e) => ({ ...e, ...m }))
    },
    factures,
    poserFacture: (devise: string, m: Partial<FactureSaisie>) => {
      marquer()
      if ('echeance' in m) setSaisies((e) => ({ ...e, [devise]: true }))
      setFactures((avant) => {
        const f: FactureSaisie = { ...(avant[devise] ?? FACTURE_VIDE), ...m }
        if ('date' in m && !saisies[devise] && f.date && fournisseur?.delai_paiement_jours)
          f.echeance = ajouterJours(f.date, fournisseur.delai_paiement_jours)
        return { ...avant, [devise]: f }
      })
    },
  }
}

/** Les bons du camion d'un brouillon : ceux que ses lignes nomment, dans l'ordre. */
const bonsDe = (r: ReceptionFiche | null) => [
  ...new Set((r?.lignes ?? []).map((l) => l.commande_id).filter((x): x is number => x != null)),
]

/** Ce que change le choix des références d'un bon : les lignes qui sortent, celles qui entrent. */
function ecartReferences(
  lignes: readonly LigneSaisie[],
  fiche: CommandeFiche,
  cochees: ReadonlySet<number>,
  nouvelle: (l: CommandeFiche['lignes'][number]) => LigneSaisie,
) {
  const du = lignes.filter((l) => l.commande_id === fiche.id)
  const presentes = new Set(du.map((l) => l.commande_ligne_id))
  return {
    sortantes: du.filter((l) => l.commande_ligne_id != null && !cochees.has(l.commande_ligne_id)),
    entrantes: fiche.lignes.filter((l) => cochees.has(l.id) && !presentes.has(l.id)).map(nouvelle),
  }
}

/**
 * Les lignes et les gestes qui les touchent ; ce qui effacerait une saisie demande d'abord.
 * Choisir un bon le met dans le camion et ouvre « Références arrivées » (`choixRefs`) : seules les
 * références cochées entrent dans la saisie, le reste demeure dû sur le bon.
 */
function useLignes(r: ReceptionFiche | null, ref: Referentiels, marquer: () => void) {
  const [lignes, setLignes] = useState<LigneSaisie[]>(
    () => r?.lignes.map((l) => depuisFiche(l, r.devise)) ?? [],
  )
  const [bons, setBons] = useState<number[]>(() => bonsDe(r))
  const [choixRefs, setChoixRefs] = useState<number | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const parMatiere = useMemo(() => new Map(ref.matieres.map((m) => [m.id, m])), [ref.matieres])
  const magasin = ref.magasins.find((m) => m.actif && m.type !== 'quarantaine')?.id ?? null
  const changer = (suite: (a: LigneSaisie[]) => LigneSaisie[]) => {
    marquer()
    setLignes(suite)
  }
  const demander = (si: boolean, texte: ReactNode, oui: string, faire: () => void) =>
    si ? setQuestion({ texte, oui, faire }) : faire()
  function ajouterBon(c: CommandeResume) {
    marquer()
    setBons((b) => (b.includes(c.id) ? b : [...b, c.id]))
    setChoixRefs(c.id)
  }
  /** Les références cochées dans « Références arrivées » : ajoutées ; les décochées : retirées. */
  function prendreReferences(fiche: CommandeFiche, cochees: ReadonlySet<number>) {
    const { sortantes, entrantes } = ecartReferences(lignes, fiche, cochees, (l) =>
      ligneDuBon(fiche, l, parMatiere.get(l.matiere_id), magasin),
    )
    const hors = new Set(sortantes.map((l) => l.cle))
    const faire = () => changer((a) => [...a.filter((l) => !hors.has(l.cle)), ...entrantes])
    setChoixRefs(null) // la question éventuelle se pose dans la saisie, au premier plan
    const saisies = sortantes.filter(estSaisie).length
    demander(saisies > 0, questionDecocher(sortantes.length, saisies), 'Oui, les retirer', faire)
  }
  return {
    lignes,
    bons,
    choixRefs,
    ouvrirReferences: (id: number) => setChoixRefs(id),
    fermerReferences: () => setChoixRefs(null),
    prendreReferences,
    vider: () => {
      changer(() => [])
      setBons([])
    },
    question,
    fermerQuestion: () => setQuestion(null),
    demander,
    ajouterBon,
    retirer: (l: LigneSaisie) =>
      demander(estSaisie(l), questionRetrait(l), 'Oui, retirer la ligne', () =>
        changer((a) => a.filter((x) => x.cle !== l.cle)),
      ),
    retirerBon: (id: number) => {
      changer((a) => a.filter((l) => l.commande_id !== id))
      setBons((b) => b.filter((x) => x !== id))
    },
    modifier: (cle: string, m: Partial<LigneSaisie>) =>
      changer((a) => a.map((l) => (l.cle === cle ? { ...l, ...m } : l))),
    ajouterLot: (l: LigneSaisie) => changer((a) => avecAutreLot(a, l)),
    ajouterHorsCommande: (m: Matiere, devise: string) =>
      changer((a) => [...a, ligneHorsCommande(m, devise, magasin)]),
  }
}

const questionDecocher = (n: number, saisies: number) =>
  `Décocher ${n} référence(s) en retire ${saisies} déjà saisie(s) (lot, pesée) : elles resteront dues sur le bon. Continuer ?`

const questionRetrait = (l: LigneSaisie) =>
  `Retirer « ${l.reference} »${l.lot_numero ? ` (lot ${l.lot_numero})` : ''} déjà saisie ?${l.commande ? ' Elle reste due sur le bon.' : ''}`

/** Les lignes avec un autre lot de `l` juste en dessous. */
function avecAutreLot(a: readonly LigneSaisie[], l: LigneSaisie): LigneSaisie[] {
  const i = a.findIndex((x) => x.cle === l.cle)
  return [...a.slice(0, i + 1), autreLot(l), ...a.slice(i + 1)]
}

/** Un autre lot de la même ligne de bon, juste en dessous (même `commande_ligne_id`). */
function autreLot(l: LigneSaisie): LigneSaisie {
  return {
    ...l,
    cle: nouvelleCle(),
    lot_numero: '',
    lot_interne: false,
    quantite_bl: null,
    quantite_pesee: null,
    nb_palettes: null,
    bobines_en_plus: null,
    qualite: 'conforme',
    observations: '',
  }
}

export function useSaisieReception(r: ReceptionFiche | null, ref: Referentiels) {
  const [modifie, setModifie] = useState(false)
  const marquer = () => setModifie(true)
  const [fournisseurId, setFournisseurId] = useState<number | null>(r?.fournisseur_id ?? null)
  const fournisseur = ref.fournisseurs.find((f) => f.id === fournisseurId) ?? null
  const e = useEnTete(r, fournisseur, marquer)
  const li = useLignes(r, ref, marquer)
  const saisies = li.lignes.filter(estSaisie).length
  function poserFournisseur(f: Fournisseur | null, bon?: CommandeResume) {
    setFournisseurId(f?.id ?? null)
    li.vider()
    const ouverts = ref.bons.filter((c) => f && c.fournisseur_id === f.id && bonOuvert(c))
    const charger = bon ?? (ouverts.length === 1 ? ouverts[0] : undefined)
    if (charger) li.ajouterBon(charger)
  }
  const effacer = `${li.lignes.length} ligne(s)`
  return {
    ...e,
    ...li,
    sale: modifie,
    fournisseur,
    fournisseurId,
    ajouterHorsCommande: (m: Matiere) => li.ajouterHorsCommande(m, fournisseur?.devise ?? ''),
    choisirFournisseur: (f: Fournisseur | null) => {
      if (f?.id === fournisseurId) return
      li.demander(
        saisies > 0,
        `Changer de fournisseur efface les ${effacer} de la réception, dont ${saisies} déjà saisie(s) (lot, pesée). Continuer ?`,
        'Oui, changer de fournisseur',
        () => poserFournisseur(f),
      )
    },
    choisirBon: (c: CommandeResume) => {
      if (c.fournisseur_id === fournisseurId) return li.ajouterBon(c)
      const f = ref.fournisseurs.find((x) => x.id === c.fournisseur_id) ?? null
      li.demander(
        saisies > 0,
        `Le bon ${c.numero} est de ${c.fournisseur} : passer à ce fournisseur efface les ${effacer} déjà là, dont ${saisies} saisie(s). Continuer ?`,
        'Oui, changer de fournisseur',
        () => poserFournisseur(f, c),
      )
    },
    basculerBon: (c: CommandeResume, dedans: boolean) => {
      if (dedans) return li.ajouterBon(c)
      const retirees = li.lignes.filter((l) => l.commande_id === c.id)
      const n = retirees.filter(estSaisie).length
      li.demander(
        n > 0,
        `Décocher le bon ${c.numero} retire ses ${retirees.length} ligne(s), dont ${n} déjà saisie(s). Continuer ?`,
        'Oui, retirer ce bon',
        () => li.retirerBon(c.id),
      )
    },
  }
}

export type SaisieReception = ReturnType<typeof useSaisieReception>
