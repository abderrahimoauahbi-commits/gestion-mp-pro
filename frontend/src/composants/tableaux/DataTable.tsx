/**
 * Le tableau de données unique (A1, A2, A6 ; AMELIORATIONS 9) : toutes les listes passent par
 * lui, un seul comportement à apprendre.
 *
 * - Recherche multi-mots sans accents, sur les colonnes **et** des champs cachés ; elle garde le
 *   focus. Filtres liés, « N critère(s) », « Effacer les filtres ».
 * - Tri au clic (ou Entrée) sur l'en-tête : numérique puis naturel ; les vides à la fin.
 * - Compteur « n / total » ; ligne cliquable (curseur, filet, Entrée) ; cellule-lien.
 * - Pas de pagination visuelle : le tableau défile dans son `Cadre` (hauteur restante, en-tête
 *   collant) ; une liste paginée au serveur finit par « Charger les 500 suivants ».
 * - Pied de totaux par unité : jamais kg + ml, jamais deux devises additionnées.
 * - Lignes de groupe (`groupe`) : une ligne d'en-tête avant chaque suite de lignes de même clé
 *   (un mois de l'échéancier et ce qui y reste à payer).
 * - Liste vide : `vide` dit pourquoi elle l'est ; `videFiltre`, ce que ne trouvent pas les critères.
 * - Export : le classeur du serveur avec la vue (onglet, recherche, filtres), ou ce qui est affiché.
 *
 * L'état (recherche, filtres) est local par défaut ; `useEtatTableAdresse` le met dans l'adresse.
 * `serveur` : la recherche et les filtres sont appliqués par le serveur (liste paginée), pas ici.
 */
import { useMemo, useState, type ReactNode } from 'react'

import { nombre } from '../../lib/format'
import { classes } from '../mise-en-page/classes'
import { Bouton } from '../saisie/Bouton'
import { useAgrandir } from './Agrandir'
import { Cadre } from './Cadre'
import { ChargerPlus, type ChargerPlusProps } from './ChargerPlus'
import { brute, champsCherches, type Colonne } from './colonnes'
import { Corps, Pied, Tete, type Groupe, type Tri } from './DataTableParties'
import styles from './DataTable.module.css'
import { ExportExcel, exporterCsv } from './ExportExcel'
import { passe, trier, trouve, type Choix, type Filtre } from './filtrage'
import { Filtres } from './Filtres'
import { Recherche } from './Recherche'

type Parametre = string | number | boolean | null | undefined

export interface DataTableProps<T> {
  lignes: readonly T[]
  colonnes: readonly Colonne<T>[]
  cle: (ligne: T) => string | number
  filtres?: readonly Filtre<T>[]
  /** Des champs cherchés qui ne sont dans aucune colonne. */
  rechercheCachee?: (ligne: T) => readonly unknown[]
  recherche?: { valeur: string; onChange: (q: string) => void } | false
  choix?: { valeurs: Choix; poser: (cle: string, valeur: string | null) => void; effacer: () => void }
  serveur?: boolean
  cliquable?: (ligne: T) => void
  marquee?: (ligne: T) => boolean
  pied?: ReactNode
  /** Le total du serveur quand la liste est paginée. */
  total?: number
  chargerPlus?: ChargerPlusProps
  vide?: ReactNode
  /** Le texte quand les critères (recherche, filtres) n'en retiennent aucune. */
  videFiltre?: ReactNode
  /** Les lignes de groupe : la clé d'une ligne, et l'en-tête de son groupe (ses lignes retenues). */
  groupe?: Groupe<T>
  exporter?: { route: string; parametres?: Record<string, Parametre> } | { fichier: string }
  outils?: ReactNode
  hauteur?: 'page' | 'court' | 'fenetre'
  triInitial?: Tri
  libelle?: string
  placeholder?: string
}

/** La recherche et les filtres : ceux de la page (adresse) s'ils sont donnés, sinon les siens. */
function useEtat<T>(props: DataTableProps<T>) {
  const [q, setQ] = useState('')
  const [choixLocal, setChoixLocal] = useState<Choix>({})
  const recherche = props.recherche === false ? null : (props.recherche ?? { valeur: q, onChange: setQ })
  const choix = props.choix ?? {
    valeurs: choixLocal,
    poser: (cle: string, v: string | null) => setChoixLocal((c) => ({ ...c, [cle]: v ?? undefined })),
    effacer: () => {
      setChoixLocal({})
      setQ('')
    },
  }
  return { recherche, choix }
}

/** Les lignes retenues par la recherche et les filtres, puis triées. */
function useLignes<T>(props: DataTableProps<T>, q: string, choix: Choix, tri: Tri | null) {
  const { lignes, colonnes, filtres = [], rechercheCachee, serveur } = props
  const dansRecherche = useMemo(() => {
    if (serveur || !q.trim()) return () => true
    return (l: T) => trouve(champsCherches(colonnes, l, rechercheCachee), q)
  }, [serveur, q, colonnes, rechercheCachee])
  const retenues = useMemo(() => {
    const r = serveur ? [...lignes] : lignes.filter((l) => passe(l, filtres, choix) && dansRecherche(l))
    const c = tri && colonnes.find((x) => x.cle === tri.cle)
    return c ? trier(r, (l) => brute(c, l), tri.sens) : r
  }, [lignes, filtres, choix, dansRecherche, serveur, tri, colonnes])
  return { retenues, dansRecherche }
}

/** L'export : le classeur du serveur avec la vue (onglet, recherche, filtres), ou ce qui est affiché. */
function Exporter<T>(p: {
  exporter: NonNullable<DataTableProps<T>['exporter']>
  q: string
  choix: Choix
  colonnes: readonly Colonne<T>[]
  lignes: readonly T[]
}) {
  const e = p.exporter
  if ('route' in e) {
    return (
      <ExportExcel route={e.route} parametres={{ ...e.parametres, q: p.q.trim() || undefined, ...p.choix }} />
    )
  }
  return (
    <Bouton taille="petit" icone="telecharger" onClick={() => exporterCsv(e.fichier, p.colonnes, p.lignes)}>
      Exporter (CSV)
    </Bouton>
  )
}

/** « n / total » : les lignes affichées sur toutes celles de la liste. */
function Compte({ affichees, total }: { affichees: number; total: number }) {
  return (
    <span
      className={styles.compteur}
      aria-live="polite"
      title={`${nombre(affichees)} lignes affichées sur ${nombre(total)}`}
    >
      {nombre(affichees)} / {nombre(total)}
    </span>
  )
}

/** Une liste vide dit pourquoi : rien du tout, ou rien qui réponde aux critères. */
function ListeVide({ vide, texte, filtre }: { vide: boolean; texte?: ReactNode; filtre?: ReactNode }) {
  return (
    <div className={styles.vide}>
      {vide ? (texte ?? 'Aucun élément.') : (filtre ?? 'Aucune ligne ne répond à ces critères.')}
    </div>
  )
}

export function DataTable<T>(props: DataTableProps<T>) {
  const { lignes, colonnes, filtres = [], exporter, hauteur = 'page' } = props
  const { recherche, choix } = useEtat(props)
  const [tri, setTri] = useState<Tri | null>(props.triInitial ?? null)
  const q = recherche?.valeur ?? ''
  const { retenues, dansRecherche } = useLignes(props, q, choix.valeurs, tri)
  const total = props.total ?? lignes.length
  const agrandir = useAgrandir<HTMLDivElement>()
  return (
    <div ref={agrandir.boite} className={classes(styles.dataTable, agrandir.classe)}>
      <div className={styles.outils}>
        {recherche ? (
          <Recherche
            valeur={recherche.valeur}
            onChange={recherche.onChange}
            placeholder={props.placeholder}
          />
        ) : null}
        {filtres.length ? (
          <Filtres
            filtres={filtres}
            lignes={lignes}
            choix={choix.valeurs}
            onChoix={choix.poser}
            onEffacer={choix.effacer}
            recherchePosee={Boolean(q.trim())}
            dansRecherche={dansRecherche}
          />
        ) : null}
        <span className={styles.pousse} />
        <Compte affichees={retenues.length} total={total} />
        {agrandir.bouton}
        {props.outils}
        {exporter ? (
          <Exporter exporter={exporter} q={q} choix={choix.valeurs} colonnes={colonnes} lignes={retenues} />
        ) : null}
      </div>
      <Cadre hauteur={hauteur}>
        <table className={styles.table} aria-label={props.libelle}>
          <Tete colonnes={colonnes} tri={tri} onTri={setTri} />
          <Corps
            colonnes={colonnes}
            lignes={retenues}
            cle={props.cle}
            cliquable={props.cliquable}
            marquee={props.marquee}
            groupe={props.groupe}
          />
          <Pied colonnes={colonnes} lignes={retenues} pied={props.pied} />
        </table>
        {retenues.length === 0 ? (
          <ListeVide vide={lignes.length === 0} texte={props.vide} filtre={props.videFiltre} />
        ) : null}
        {props.chargerPlus ? <ChargerPlus {...props.chargerPlus} /> : null}
      </Cadre>
    </div>
  )
}
