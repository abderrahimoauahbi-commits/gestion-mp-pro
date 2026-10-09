/**
 * « Sorties vers les machines » (`/sorties?onglet=valide|brouillon|annule`) : chaque ordre de
 * fabrication, la matière partie, les retours, et l'écart avec ce que prévoit la recette. Par-dessus
 * la liste, à adresse stable (A5) : la fiche `/ordres/:id`, la saisie `/ordres/nouveau` (un brouillon
 * se modifie dans sa fiche), le retour `/ordres/:id/retour`. Écriture : direction, alimentation.
 */
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router'

import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { champsCherches } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import { passe, trouve, type Filtre } from '../../composants/tableaux/filtrage'
import { avecParametre } from '../../lib/adresse'
import { kg, nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Role } from '../../lib/types'
import { Periode } from '../stock/Periode'
import styles from '../stock/stock.module.css'
import { colonnesOrdres } from './colonnesOrdres'
import { useOrdre, useOrdres, type OrdreFiche, type OrdreResume, type StatutOrdre } from './donnees'
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

const dansPeriode = (o: OrdreResume, du?: string, au?: string) =>
  (!du || o.date >= du) && (!au || o.date <= au)

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

function useListe(onglet: StatutOrdre, role: Role) {
  const ordres = useOrdres()
  const table = useEtatTableAdresse(CLES_SORTIES)
  const v = table.choix.valeurs
  const toutes = ordres.data ?? []
  const periode = toutes.filter((o) => dansPeriode(o, v.du, v.au))
  const avant = periode.filter(
    (o) => o.statut === onglet && (!v.qualite || o.qualites.some((q) => q.qualite === v.qualite)),
  )
  const filtres: Filtre<OrdreResume>[] = [
    { cle: 'metier', libelle: 'Métier', valeur: (o) => o.metier },
    { cle: 'magasin', libelle: 'Magasin', valeur: (o) => o.magasin },
  ]
  const colonnes = colonnesOrdres(onglet === 'brouillon', role)
  const affiches = avant.filter(
    (o) => passe(o, filtres, v) && trouve(champsCherches(colonnes, o), table.recherche.valeur),
  )
  const qualites = [
    ...new Set(periode.filter((o) => o.statut === onglet).flatMap((o) => o.qualites.map((q) => q.qualite))),
  ].sort()
  return { ordres, table, v, periode, avant, filtres, colonnes, affiches, qualites }
}

type Liste = ReturnType<typeof useListe>

function Outils({ l }: { l: Liste }) {
  return (
    <>
      <select
        aria-label="Qualité"
        className={styles.selecteur}
        value={l.v.qualite ?? ''}
        onChange={(e) => l.table.choix.poser('qualite', e.target.value || null)}
      >
        <option value="">Qualité : toutes</option>
        {l.qualites.map((q) => (
          <option key={q}>{q}</option>
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
  const kilos = l.affiches.reduce((t, o) => t + (brouillons ? o.total : o.net), 0)
  return (
    <Carte
      titre={ONGLETS.find((o) => o.cle === onglet)?.libelle}
      sous={`${nombre(l.affiches.length)} ordre(s) · ${kg(kilos)} ${brouillons ? 'à sortir à la validation.' : 'sortis nets, retours déduits.'}`}
      actions={
        <>
          {brouillons && l.affiches.length ? (
            <Link
              to="/stock?onglet=a-valider"
              title="Tous les brouillons (ordres et opérations), avec ce qui les bloquerait, et « Tout valider »"
            >
              Tout valider…
            </Link>
          ) : null}
          <ExportExcel
            route="/export/ordres"
            parametres={{
              statut: onglet,
              du: l.v.du,
              au: l.v.au,
              q: l.table.recherche.valeur.trim() || undefined,
            }}
          />
        </>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<OrdreResume>
        libelle="Ordres de fabrication"
        lignes={l.avant}
        colonnes={l.colonnes}
        filtres={l.filtres}
        cle={(o) => o.id}
        recherche={l.table.recherche}
        choix={l.table.choix}
        marquee={(o) => o.blocages.length > 0}
        placeholder="N° d’ordre, qualité, matière, lot, métier, commentaire…"
        cliquable={(o) => navigate(`/ordres/${o.id}${search}`)}
        vide="Aucun ordre dans cet onglet."
        outils={<Outils l={l} />}
      />
    </Carte>
  )
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
      {l.ordres.isPending ? <Chargement quoi="les ordres" /> : null}
      {l.ordres.isError ? (
        <Erreur erreur={l.ordres.error} onReessayer={() => void l.ordres.refetch()} />
      ) : null}
      <IndicateursSorties
        affiches={l.affiches}
        periode={l.periode}
        brouillons={onglet === 'brouillon'}
        du={l.v.du}
        au={l.v.au}
      />
      <Onglets<StatutOrdre>
        libelle="Onglets des sorties"
        actif={onglet}
        onChange={choisir}
        onglets={ONGLETS.map((o) => ({ ...o, compte: l.periode.filter((x) => x.statut === o.cle).length }))}
      />
      <CarteOrdres l={l} onglet={onglet} />
      <Ouvert ouvert={ouvert} ecrit={ecrit} />
    </Page>
  )
}
