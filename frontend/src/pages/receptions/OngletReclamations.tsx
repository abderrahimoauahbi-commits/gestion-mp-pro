/**
 * Réceptions › Réclamations (ECRANS-PRO 4.22) : les indicateurs (ouvertes, closes, délai de
 * réponse, obtenu par devise), la bascule Ouvertes · Closes · Toutes dans l'adresse (`?etat=`),
 * la recherche et les filtres liés ; une ligne ouvre la réclamation.
 */
import { useMemo, type ReactNode } from 'react'
import { Link } from 'react-router'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { formule } from '../../lib/aide'
import { date, montant, montants, nombre, VIDE } from '../../lib/format'
import { useChoixAdresse } from '../commandes/adresse'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { useReclamations } from './donnees'
import type { ReclamationResume } from './types'

const ETATS = ['ouvertes', 'closes', 'toutes'] as const
type Etat = (typeof ETATS)[number]
export const CLES_FILTRES_RECLAMATIONS = ['fournisseur', 'motif', 'issue', 'etat'] as const

function IndicateursReclamations({ i }: { i: ReturnType<typeof indicateursReclamations> }) {
  return (
    <Indicateurs libelle="Indicateurs des réclamations">
      <Kpi
        titre="Ouvertes"
        valeur={nombre(i.ouvertes)}
        formule={formule('reclamations_ouvertes')}
        ton={i.ouvertes ? 'attention' : 'ok'}
        detail={
          i.anciennes ? `dont ${nombre(i.anciennes)} depuis plus de 30 jours` : 'en attente du fournisseur'
        }
      />
      <Kpi
        titre="Closes"
        valeur={nombre(i.closes)}
        formule={formule('reclamations_closes')}
        detail="réponse obtenue ou abandon"
      />
      <Kpi
        titre="Délai de réponse"
        valeur={i.delai == null ? VIDE : `${nombre(i.delai, 0, 1)} j`}
        formule={formule('reclamations_delai')}
        detail="en moyenne, des closes"
      />
      <Kpi
        titre="Obtenu"
        valeur={montants(i.obtenu)}
        formule={formule('reclamations_obtenu')}
        detail="avoirs et remises, par devise"
      />
    </Indicateurs>
  )
}

export function indicateursReclamations(liste: readonly ReclamationResume[]) {
  const ouvertes = liste.filter((r) => r.statut === 'ouverte')
  const closes = liste.filter((r) => r.statut !== 'ouverte')
  const obtenu: Record<string, number> = {}
  for (const r of liste) if (r.montant_obtenu) obtenu[r.devise] = (obtenu[r.devise] ?? 0) + r.montant_obtenu
  return {
    ouvertes: ouvertes.length,
    anciennes: ouvertes.filter((r) => r.jours > 30).length,
    closes: closes.length,
    delai: closes.length ? closes.reduce((s, r) => s + r.jours, 0) / closes.length : null,
    obtenu,
  }
}

const COLONNES: Colonne<ReclamationResume>[] = [
  { cle: 'numero', titre: 'N°', rendu: (r) => <span className={styles.sansCoupure}>{r.numero}</span> },
  { cle: 'ouverte_le', titre: 'Ouverte le', rendu: (r) => date(r.ouverte_le) },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'reception',
    titre: 'Réception · lot',
    valeur: (r) => r.reception || 'sans réception',
    rendu: (r) =>
      deux(
        r.reception_id ? (
          <Link to={`/receptions/${r.reception_id}`} onClick={(e) => e.stopPropagation()}>
            {r.reception || 'Brouillon'}
          </Link>
        ) : (
          <span className={styles.note}>sans réception</span>
        ),
        [r.lot ? `lot ${r.lot}` : '', r.reference].filter(Boolean).join(' · ') || null,
      ),
  },
  {
    cle: 'motif',
    titre: 'Motif',
    valeur: (r) => r.motif_libelle,
    rendu: (r) =>
      deux(
        r.motif_libelle,
        r.description ? (r.description.length > 80 ? `${r.description.slice(0, 80)}…` : r.description) : null,
      ),
  },
  {
    cle: 'quantite',
    titre: 'Quantité (kg)',
    droite: true,
    rendu: (r) => (r.quantite ? nombre(r.quantite) : VIDE),
  },
  {
    cle: 'montant_demande',
    titre: 'Demandé',
    droite: true,
    unite: (r) => r.devise,
    total: true,
    rendu: (r) => (r.montant_demande ? montant(r.montant_demande, r.devise) : VIDE),
  },
  {
    cle: 'montant_obtenu',
    titre: 'Obtenu',
    droite: true,
    unite: (r) => r.devise,
    total: true,
    rendu: (r) => (r.montant_obtenu ? montant(r.montant_obtenu, r.devise) : VIDE),
  },
  {
    cle: 'issue',
    titre: 'Issue',
    valeur: (r) => (r.issue ? r.issue_libelle : 'ouverte'),
    rendu: (r) =>
      r.issue ? (
        <Badge famille="issue_reclamation" valeur={r.issue} />
      ) : (
        <Badge famille="reclamation" valeur="ouverte" />
      ),
  },
  {
    cle: 'jours',
    titre: 'Durée',
    aide: 'Depuis l’ouverture (jusqu’à la clôture pour une close)',
    droite: true,
    rendu: (r) =>
      r.statut === 'ouverte' && r.jours > 30 ? (
        <Badge ton="critique">{`${nombre(r.jours)} j`}</Badge>
      ) : (
        `${nombre(r.jours)} j`
      ),
  },
]

const CHERCHES = (r: ReclamationResume) => [
  r.description,
  r.reponse,
  r.issue_libelle,
  r.lot,
  r.reference,
  r.numero_bl,
]

function filtres(noms: ReadonlyMap<string, string>): Filtre<ReclamationResume>[] {
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (r) => String(r.fournisseur_id),
      libelleValeur: (v) => noms.get(v) ?? v,
    },
    { cle: 'motif', libelle: 'Motif', valeur: (r) => r.motif_libelle },
    { cle: 'issue', libelle: 'Issue', valeur: (r) => (r.issue ? r.issue_libelle : 'ouverte') },
  ]
}

/** La carte de la liste : la bascule Ouvertes · Closes · Toutes en titre, « Nouvelle réclamation ». */
function CarteReclamations({
  i,
  vue,
  choisir,
  onNouvelle,
  children,
}: {
  i: ReturnType<typeof indicateursReclamations>
  vue: Etat
  choisir: (v: Etat) => void
  onNouvelle: () => void
  children: ReactNode
}) {
  return (
    <Carte
      titre={
        <Bascule<Etat>
          libelle="Réclamations"
          valeur={vue}
          onChange={choisir}
          vues={[
            { cle: 'ouvertes', libelle: `Ouvertes (${nombre(i.ouvertes)})` },
            { cle: 'closes', libelle: `Closes (${nombre(i.closes)})` },
            { cle: 'toutes', libelle: 'Toutes' },
          ]}
        />
      }
      actions={
        <Bouton
          icone="plus"
          titre="Une réclamation sans réception : un retard, une facture fausse…"
          onClick={onNouvelle}
        >
          Nouvelle réclamation
        </Bouton>
      }
      serre
      remplir
      className={styles.carteListe}
    >
      {children}
    </Carte>
  )
}

export function OngletReclamations({
  etat,
  onOuvrir,
  onNouvelle,
}: {
  etat: EtatTable
  onOuvrir: (id: number) => void
  onNouvelle: () => void
}) {
  const lu = useReclamations()
  const [vue, choisir] = useChoixAdresse<Etat>('etat', ETATS, 'ouvertes')
  const liste = useMemo(() => lu.data ?? [], [lu.data])
  const i = indicateursReclamations(liste)
  const noms = useMemo(() => new Map(liste.map((r) => [String(r.fournisseur_id), r.fournisseur])), [liste])
  const lignes = liste.filter((r) => vue === 'toutes' || (vue === 'ouvertes') === (r.statut === 'ouverte'))
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  if (!lu.data) return <Chargement quoi="les réclamations" />
  return (
    <>
      <IndicateursReclamations i={i} />
      <CarteReclamations i={i} vue={vue} choisir={choisir} onNouvelle={onNouvelle}>
        <DataTable<ReclamationResume>
          libelle="Réclamations"
          lignes={lignes}
          colonnes={COLONNES}
          filtres={filtres(noms)}
          cle={(r) => r.id}
          recherche={etat.recherche}
          choix={etat.choix}
          rechercheCachee={CHERCHES}
          placeholder="Fournisseur, lot, motif, n°…"
          cliquable={(r) => onOuvrir(r.id)}
          vide={
            liste.length
              ? 'Aucune réclamation ne correspond.'
              : 'Aucune réclamation. Un défaut à la réception ? Ouvrez la réception, puis « Réclamer au fournisseur ».'
          }
        />
      </CarteReclamations>
    </>
  )
}
