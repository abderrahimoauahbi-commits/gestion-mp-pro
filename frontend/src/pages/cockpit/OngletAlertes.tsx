/**
 * Cockpit › Matières en alerte (`/cockpit?onglet=alertes`) : **toutes** les matières aux statuts
 * RUPTURE, CRITIQUE, URGENT, ATTENTION (GET /stock, P1-13 : plus de limite à 24), la plus pressée
 * d'abord (couverture croissante, comme le serveur), recherche et filtres liés sur tout le jeu.
 * Une ligne ouvre la fiche matière ; « Préparer la commande » ouvre la préparation chez son
 * fournisseur (identifiant lu dans le catalogue, jamais par le nom).
 */
import { Link, useNavigate } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useEtatTableAdresse } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { jours, nombre, VIDE } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { cleStock, STATUTS, STOCK_EN_ALERTE } from '../../lib/statuts'
import type { Role, Schema } from '../../lib/types'
import { siPermis } from '../accueil/taches'
import type { Cockpit } from '../accueil/types'
import { Double, Kg } from '../stock/cellules'
import { rangStatut } from '../stock/colonnesMatieres'

type LigneStock = Schema<'LigneStock'>
type EtatStock = Schema<'EtatStock'>
type MatiereResume = Schema<'MatiereResume'>

export interface LigneAlerte extends LigneStock {
  fournisseur_id: number | null
}

/** Les matières en alerte (quatre statuts), la plus pressée d'abord (couverture croissante). */
export function lignesEnAlerte(
  stock: EtatStock | undefined,
  matieres: readonly MatiereResume[] | undefined,
): LigneAlerte[] {
  const fournisseurs = new Map((matieres ?? []).map((m) => [m.id, m.fournisseur_id]))
  return (stock?.lignes ?? [])
    .filter((l) => STOCK_EN_ALERTE.includes(cleStock(l.statut) ?? ''))
    .map((l) => ({ ...l, fournisseur_id: (l.matiere_id != null && fournisseurs.get(l.matiere_id)) || null }))
    .sort((a, b) => (a.couverture_jours ?? 0) - (b.couverture_jours ?? 0))
}

const kg = (cle: string, titre: string, v: (l: LigneAlerte) => number | null | undefined, aide?: string) =>
  ({
    cle,
    titre,
    aide,
    droite: true,
    unite: 'kg',
    valeur: (l) => v(l) ?? null,
    rendu: (l) => <Kg v={v(l)} kgParMl={l.kg_par_ml} d={0} />,
  }) satisfies Colonne<LigneAlerte>

const IDENTITE: Colonne<LigneAlerte>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    valeur: (l) => l.reference,
    recherche: (l) => [l.designation, l.nature, l.titrage, l.statut_couverture],
    rendu: (l) => (
      <Double haut={l.reference} bas={[l.nature, l.titrage, l.designation].filter(Boolean).join(' · ')} />
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur', valeur: (l) => l.fournisseur ?? '' },
  {
    ...kg(
      'projete',
      'Stock projeté (kg)',
      (l) => l.stock_projete,
      'Stock détenu (magasins et métiers) + commandé à temps − sorties prévues pendant le délai',
    ),
    rendu: (l) => (
      <Double
        haut={<Kg v={l.stock_projete} kgParMl={l.kg_par_ml} d={0} />}
        bas={l.stock_machine ? `dont ${nombre(l.stock_machine)} kg sur les métiers` : ''}
      />
    ),
  },
  kg('conso', 'Conso / mois (kg)', (l) => l.conso_mensuelle),
  {
    cle: 'couverture',
    titre: 'Couverture',
    droite: true,
    valeur: (l) => l.couverture_jours ?? null,
    rendu: (l) => (l.couverture_jours == null ? VIDE : jours(l.couverture_jours)),
  },
  {
    cle: 'delai',
    titre: 'Délai',
    droite: true,
    valeur: (l) => l.delai_jours,
    rendu: (l) => jours(l.delai_jours),
  },
  kg('commander', 'À commander (kg)', (l) => l.quantite_a_commander),
  {
    cle: 'statut',
    titre: 'Statut',
    aide: 'Le stock projeté face au seuil d’alerte (délai du fournisseur, sécurité, stock minimum)',
    valeur: (l) => rangStatut(l.statut),
    recherche: (l) => [l.statut],
    rendu: (l) => {
      const autre = cleStock(l.statut_couverture) !== cleStock(l.statut)
      return (
        <Badge
          famille="stock"
          valeur={cleStock(l.statut)}
          titre={
            autre
              ? `Statut de couverture : ${STATUTS.stock[cleStock(l.statut_couverture) ?? 'OK']?.libelle}`
              : undefined
          }
        />
      )
    },
  },
]

function colonnes(role: Role, preparer: (l: LigneAlerte) => string | null): Colonne<LigneAlerte>[] {
  return [
    ...IDENTITE,
    {
      cle: 'action',
      titre: 'Action',
      exporte: false,
      triable: false,
      rendu: (l) => {
        const vers = preparer(l)
        return vers && role !== 'alimentation' ? (
          <Link to={vers} title={`Commander chez ${l.fournisseur} : ouvrir la préparation de commande`}>
            Préparer la commande
          </Link>
        ) : (
          VIDE
        )
      },
    },
  ]
}

const FILTRES: Filtre<LigneAlerte>[] = [
  {
    cle: 'statut',
    libelle: 'Statut',
    valeur: (l) => cleStock(l.statut),
    libelleValeur: (v) => Object.entries(STATUTS.stock).find(([k]) => k === v)?.[1].libelle ?? v,
  },
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
]

export function OngletAlertes({ cockpit }: { cockpit: Cockpit }) {
  const { role } = useSession()
  const navigate = useNavigate()
  const stock = useLecture<EtatStock>('/stock')
  const matieres = useLecture<MatiereResume[]>('/matieres')
  const etat = useEtatTableAdresse(['statut', 'fournisseur'])
  const lignes = lignesEnAlerte(stock.data, matieres.data)
  const preparer = (l: LigneAlerte) =>
    l.fournisseur_id && (l.quantite_a_commander ?? 0) > 0
      ? siPermis(role, `/plan-achat/preparer/${l.fournisseur_id}`)
      : null
  const s = cockpit.stock
  const plan = siPermis(role, '/plan-achat')
  return (
    <Carte
      titre={`Matières en alerte, la plus pressée d’abord — ${nombre(lignes.length)}`}
      sous={`${nombre(cockpit.alerte_rouge)} en rupture ou critiques, ${nombre(s.urgents)} URGENT, ${nombre(s.attentions)} en ATTENTION`}
      actions={
        <>
          {plan ? <Link to={plan}>Plan d’achat →</Link> : null}
          <Link to="/stock">Stock →</Link>
        </>
      }
      serre
      remplir
    >
      {stock.isPending || matieres.isPending ? <Chargement quoi="les matières en alerte" /> : null}
      <Erreur erreur={stock.error ?? matieres.error} onReessayer={() => void stock.refetch()} />
      {stock.data ? (
        <DataTable
          lignes={lignes}
          colonnes={colonnes(role, preparer)}
          cle={(l) => l.reference ?? String(l.matiere_id)}
          filtres={FILTRES}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Référence, fournisseur, statut… plusieurs mots"
          cliquable={(l) => {
            const vers = l.matiere_id != null ? siPermis(role, `/stock/matieres/${l.matiere_id}`) : null
            if (vers) navigate(vers)
          }}
          libelle="Matières en alerte"
          vide="Aucune matière en alerte."
          exporter={{ fichier: 'matieres-en-alerte' }}
        />
      ) : null}
    </Carte>
  )
}
