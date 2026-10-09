/**
 * « Sorties vers les machines » (`/sorties?onglet=valide|brouillon|annule`) : chaque ordre de
 * fabrication, la matière partie, les retours, et l'écart avec ce que prévoit la recette. La liste
 * est **paginée au serveur** (recherche, filtres et agrégats poussés en SQL/au moteur ; mêmes
 * chiffres qu'avant). Par-dessus la liste, à adresse stable (A5) : la fiche `/ordres/:id`, la
 * saisie `/ordres/nouveau` (un brouillon se modifie dans sa fiche), le retour `/ordres/:id/retour`.
 * Écriture : direction, alimentation.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse, type EtatTable } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { avecParametre } from '../../lib/adresse'
import { kg, nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import { Periode } from '../stock/Periode'
import styles from '../stock/stock.module.css'
import { colonnesOrdres } from './colonnesOrdres'
import {
  useApercuOrdres,
  useOrdre,
  type ApercuOrdres,
  type OptionOrdres,
  type OrdreFiche,
  type OrdreResume,
  type StatutOrdre,
} from './donnees'
import { FicheOrdre } from './FicheOrdre'
import { IndicateursSorties } from './IndicateursSorties'
import { RetourMachines } from './RetourMachines'
import { SaisieOrdre } from './SaisieOrdre'

const ONGLETS: readonly { cle: StatutOrdre; libelle: string }[] = [
  { cle: 'valide', libelle: 'Validés' },
  { cle: 'brouillon', libelle: 'Brouillons' },
  { cle: 'annule', libelle: 'Annulés' },
]

export type OuvertSorties =
  { genre: 'saisie' } | { genre: 'fiche'; id: number } | { genre: 'retour'; id: number } | null

export function ouvertDe(chemin: string): OuvertSorties {
  if (chemin === '/ordres/nouveau') return { genre: 'saisie' }
  const m = /^\/ordres\/(\d+)(\/retour)?$/.exec(chemin)
  if (!m) return null
  return m[2] ? { genre: 'retour', id: Number(m[1]) } : { genre: 'fiche', id: Number(m[1]) }
}

export const CLES_SORTIES = ['metier', 'magasin', 'qualite', 'du', 'au'] as const

/** Les paramètres de la route 135 : l'onglet, les dates, les filtres liés (id) et la recherche. */
function parametres(onglet: StatutOrdre, etat: EtatTable) {
  const choix = etat.choix.valeurs
  return {
    statut: onglet,
    du: choix.du || undefined,
    au: choix.au || undefined,
    qualite: choix.qualite || undefined,
    metier: choix.metier || undefined,
    magasin: choix.magasin || undefined,
    q: etat.recherche.valeur.trim() || undefined,
  }
}

/** Un filtre lié dont les options (id → libellé) viennent de l'aperçu du serveur. */
function filtreLie(
  cle: 'metier' | 'magasin',
  libelle: string,
  valeur: (o: OrdreResume) => string | null,
  options: readonly OptionOrdres[],
): Filtre<OrdreResume> {
  const noms = new Map(options.map((o) => [o.valeur, o.libelle]))
  return {
    cle,
    libelle,
    valeur,
    libelleValeur: (v) => noms.get(v) ?? v,
    options: options.map((o) => o.valeur),
  }
}

/** Le pied du serveur : Σ prévu et Σ sorti net de **tout** le filtre, alignés sous leurs colonnes. */
function PiedServeur({ colonnes, apercu }: { colonnes: Colonne<OrdreResume>[]; apercu?: ApercuOrdres }) {
  const visibles = colonnes.filter((c) => !c.cache)
  const valeur = (cle: string) => (cle === 'prevu' ? apercu?.prevu : cle === 'net' ? apercu?.net : undefined)
  return (
    <tr>
      {visibles.map((c, i) => {
        const v = valeur(c.cle)
        return (
          <td key={c.cle} className={c.droite ? 'nombre' : undefined}>
            {v != null ? kg(v) : i === 0 ? 'Total' : ''}
          </td>
        )
      })}
    </tr>
  )
}

function useListe(onglet: StatutOrdre, role: Role) {
  const table = useEtatTableAdresse(CLES_SORTIES)
  const params = parametres(onglet, table)
  const liste = useListePaginee<OrdreResume>('/ordres', params)
  const apercu = useApercuOrdres(params)
  const a = apercu.data
  const colonnes = useMemo(() => colonnesOrdres(onglet === 'brouillon', role), [onglet, role])
  const filtres = useMemo<Filtre<OrdreResume>[]>(
    () => [
      filtreLie(
        'metier',
        'Métier',
        (o) => (o.metier_id == null ? null : String(o.metier_id)),
        a?.metiers ?? [],
      ),
      filtreLie('magasin', 'Magasin', (o) => String(o.magasin_id), a?.magasins ?? []),
    ],
    [a?.metiers, a?.magasins],
  )
  return { table, v: table.choix.valeurs, liste, apercu: a, colonnes, filtres }
}

type Liste = ReturnType<typeof useListe>

function Outils({ l }: { l: Liste }) {
  const qualites = l.apercu?.qualites ?? []
  return (
    <>
      <select
        aria-label="Qualité"
        className={styles.selecteur}
        value={l.v.qualite ?? ''}
        onChange={(e) => l.table.choix.poser('qualite', e.target.value || null)}
      >
        <option value="">Qualité : toutes</option>
        {qualites.map((q) => (
          <option key={q.valeur} value={q.valeur}>
            {q.libelle}
          </option>
        ))}
      </select>
      <Periode choix={l.table.choix} />
    </>
  )
}

function CarteOrdres({ l, onglet }: { l: Liste; onglet: StatutOrdre }) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const brouillons = onglet === 'brouillon'
  const kilos = l.apercu?.net ?? 0
  return (
    <Carte
      titre={ONGLETS.find((o) => o.cle === onglet)?.libelle}
      sous={`${nombre(l.liste.total)} ordre(s) · ${kg(kilos)} ${brouillons ? 'à sortir à la validation.' : 'sortis nets, retours déduits.'}`}
      actions={
        brouillons && l.liste.total ? (
          <Link
            to="/stock?onglet=a-valider"
            title="Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout valider »"
          >
            Tout valider…
          </Link>
        ) : null
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<OrdreResume>
        libelle="Ordres de fabrication"
        serveur
        lignes={l.liste.lignes}
        total={l.liste.total}
        chargerPlus={l.liste.chargerPlus}
        colonnes={l.colonnes}
        filtres={l.filtres}
        cle={(o) => o.id}
        recherche={l.table.recherche}
        choix={l.table.choix}
        marquee={(o) => o.blocages.length > 0}
        pied={l.liste.lignes.length ? <PiedServeur colonnes={l.colonnes} apercu={l.apercu} /> : undefined}
        placeholder="N° d’ordre, qualité, matière, lot, métier, commentaire…"
        cliquable={(o) => navigate(`/ordres/${o.id}${search}`)}
        vide={
          l.liste.requete.isPending
            ? 'Chargement…'
            : l.table.recherche.valeur.trim()
              ? 'Aucun ordre ne correspond (voir les autres onglets).'
              : 'Aucun ordre dans cet onglet.'
        }
        exporter={{ route: '/export/ordres', parametres: { statut: onglet } }}
        outils={<Outils l={l} />}
      />
    </Carte>
  )
}

/** La fiche d'un brouillon passe en saisie sur place (« Modifier », même adresse). */
function FicheOuSaisie({
  id,
  onFermer,
  onFait,
}: {
  id: number
  onFermer: () => void
  onFait: (b: OrdreFiche) => void
}) {
  const [modifier, setModifier] = useState(false)
  const fiche = useOrdre(id)
  if (modifier && fiche.data?.statut === 'brouillon')
    return (
      <SaisieOrdre
        fiche={fiche.data}
        onFermer={() => setModifier(false)}
        onFait={(b) => {
          setModifier(false)
          onFait(b)
        }}
      />
    )
  return <FicheOrdre id={id} onFermer={onFermer} onModifier={() => setModifier(true)} />
}

/** Ce que l'adresse ouvre par-dessus la liste : la saisie, la fiche (ou sa saisie), le retour. */
function Ouvert({ ouvert, ecrit }: { ouvert: OuvertSorties; ecrit: boolean }) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const fermer = () => navigate(`/sorties${search}`)
  const apresSaisie = (b: OrdreFiche) =>
    navigate(`/ordres/${b.id}${b.statut === 'brouillon' ? '?onglet=brouillon' : ''}`, { replace: true })
  if (ouvert?.genre === 'saisie' && ecrit)
    return <SaisieOrdre fiche={null} onFermer={fermer} onFait={apresSaisie} />
  if (ouvert?.genre === 'fiche')
    return <FicheOuSaisie key={ouvert.id} id={ouvert.id} onFermer={fermer} onFait={apresSaisie} />
  if (ouvert?.genre === 'retour' && ecrit)
    return <RetourMachines id={ouvert.id} onFermer={() => navigate(`/ordres/${ouvert.id}${search}`)} />
  return null
}

export default function Sorties() {
  const { role } = useSession()
  const { pathname, search } = useLocation()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const ouvert = ouvertDe(pathname)
  const onglet = ONGLETS.find((o) => o.cle === params.get('onglet'))?.cle ?? 'valide'
  const l = useListe(onglet, role)
  const ancien = params.get('ordre')
  useEffect(() => {
    if (pathname === '/sorties' && ancien && /^\d+$/.test(ancien))
      navigate(`/ordres/${ancien}`, { replace: true })
  }, [pathname, ancien, navigate])
  const ecrit = role === 'direction' || role === 'alimentation'
  const choisir = (o: StatutOrdre) => {
    const p = avecParametre(params, 'onglet', o === 'valide' ? null : o).toString()
    navigate(`/sorties${p ? `?${p}` : ''}`, { replace: true })
  }
  const a = l.apercu
  return (
    <Page titre="Sorties vers les machines">
      <EnTete
        titre="Sorties vers les machines"
        sous="Chaque ordre de fabrication : la matière partie, les retours, et l'écart avec ce que prévoit la recette."
        aide="sorties"
        actions={
          ecrit ? (
            <Bouton variante="principal" icone="plus" onClick={() => navigate(`/ordres/nouveau${search}`)}>
              Nouvelle sortie
            </Bouton>
          ) : null
        }
      />
      {l.liste.requete.isError ? (
        <Erreur erreur={l.liste.requete.error} onReessayer={() => void l.liste.requete.refetch()} />
      ) : null}
      <IndicateursSorties
        total={l.liste.total}
        net={a?.net ?? 0}
        revenu={a?.revenu ?? 0}
        prevu={a?.prevu ?? 0}
        sorti={a?.sorti ?? 0}
        brouillonsPeriode={a?.brouillons_periode ?? 0}
        brouillonsBloques={a?.brouillons_bloques ?? 0}
        brouillons={onglet === 'brouillon'}
        du={l.v.du}
        au={l.v.au}
      />
      <Onglets<StatutOrdre>
        libelle="Onglets des sorties"
        actif={onglet}
        onChange={choisir}
        onglets={ONGLETS.map((o) => ({ ...o, compte: a ? a[o.cle] : null }))}
      />
      <CarteOrdres l={l} onglet={onglet} />
      <Ouvert ouvert={ouvert} ecrit={ecrit} />
    </Page>
  )
}
