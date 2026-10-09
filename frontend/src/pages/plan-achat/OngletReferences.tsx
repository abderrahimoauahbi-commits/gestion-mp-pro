/**
 * Plan d'achat › Références à commander (ECRANS-PRO 4.3) : triées par le serveur (montant pondéré
 * par la classe ABC), en-têtes triables, filtres liés (statut, priorité, classe, fournisseur), pied
 * de totaux. La référence mène à sa fiche de stock, le fournisseur à la préparation.
 */

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { KgEtMetres } from '../../composants/retour/KgEtMetres'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { jours, montant, nombre, VIDE } from '../../lib/format'
import { cleStock, statut } from '../../lib/statuts'
import type { Role } from '../../lib/types'
import styles from './achats.module.css'
import { deux } from './colonnesFournisseurs'
import { adresseMatiere, lienSi } from './liens'
import { bonsEnPreparation, cleTier, libelleTier, quantiteEnUnite } from './libelles'
import type { LignePlan } from './types'

const TITRE = 'Références à commander, triées par montant pondéré par la classe ABC (× 3 en A, × 2 en B)'
const AIDE =
  'Toutes les références que le budget compte. Une ligne au statut OK est une commande de réapprovisionnement : son stock couvre le délai, mais pas la couverture visée.'

function Statut({ l }: { l: LignePlan }) {
  const cle = cleStock(l.statut)
  return deux(<Badge famille="stock" valeur={cle} />, cle === 'OK' ? 'réapprovisionnement' : null)
}

function ACommander({ l }: { l: LignePlan }) {
  const unites =
    l.unite_commande && l.unite_commande !== 'kg' ? quantiteEnUnite(l.unites_commande, l.unite_commande) : ''
  const prep = l.en_preparation
    ? `déjà en préparation : ${nombre(l.en_preparation)} kg (${bonsEnPreparation(l.bons_en_preparation)})`
    : ''
  return (
    <>
      <KgEtMetres kg={l.quantite} kgParMl={l.kg_par_ml || null} />
      {unites ? <span className={styles.dessous}>{unites}</span> : null}
      {l.palettes && l.unite_commande !== 'Palette' ? (
        <span className={styles.dessous}>{`${nombre(l.palettes, 0, 1)} palette(s)`}</span>
      ) : null}
      {prep ? <span className={styles.dessous}>{prep}</span> : null}
    </>
  )
}

function colonnes1(preparer: (id: number) => void, role: Role): Colonne<LignePlan>[] {
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      lien: (l) => (l.matiere_id ? lienSi(role, adresseMatiere(l.matiere_id)) : null),
      rendu: (l) => (
        <span title={l.relance}>
          {deux(
            <span className={styles.ref}>{l.reference}</span>,
            [l.nature, l.designation].filter(Boolean).join(' · '),
          )}
        </span>
      ),
      recherche: (l) => [
        l.nature,
        l.designation,
        l.risque,
        l.action,
        l.classe_abc ? `classe ${l.classe_abc}` : '',
      ],
    },
    {
      cle: 'fournisseur',
      titre: 'Fournisseur',
      rendu: (l) =>
        l.fournisseur_id ? (
          <button
            type="button"
            className={styles.lien}
            title="Préparer la commande de ce fournisseur"
            onClick={() => preparer(l.fournisseur_id ?? 0)}
          >
            {l.fournisseur}
          </button>
        ) : (
          l.fournisseur
        ),
    },
  ]
}

function colonnes2(): Colonne<LignePlan>[] {
  return [
    {
      cle: 'classe_abc',
      titre: 'ABC',
      aide: 'Classe ABC : A, les matières qui pèsent le plus dans la consommation en valeur',
    },
    {
      cle: 'statut',
      titre: 'Statut',
      valeur: (l) => statut('stock', cleStock(l.statut)).libelle,
      rendu: (l) => <Statut l={l} />,
    },
    {
      cle: 'stock_disponible',
      titre: 'Disponible (kg)',
      aide: 'En stock, hors quarantaine ; dessous, le commandé : bons partis, attendus',
      droite: true,
      rendu: (l) =>
        deux(nombre(l.stock_disponible), l.commande_kg ? `+ ${nombre(l.commande_kg)} commandé` : null),
    },
    {
      cle: 'couverture_jours',
      titre: 'Couverture',
      aide: 'Jours de consommation que couvre le stock projeté',
      droite: true,
      rendu: (l) => (l.couverture_jours == null ? VIDE : jours(l.couverture_jours)),
    },
    {
      cle: 'quantite',
      titre: 'À commander (kg)',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (l) => <ACommander l={l} />,
    },
  ]
}

function colonnes3(): Colonne<LignePlan>[] {
  return [
    {
      cle: 'montant_mad',
      titre: 'Montant',
      aide: 'Au prix du catalogue ; en MAD au cours du jour',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (l) =>
        deux(montant(l.montant_devise, l.devise), l.devise !== 'MAD' ? montant(l.montant_mad, 'MAD') : null),
    },
    {
      cle: 'tier',
      titre: 'Priorité · action',
      valeur: (l) => libelleTier(l.tier),
      rendu: (l) =>
        deux(
          <Badge famille="tier" valeur={cleTier(l.tier)} />,
          [l.action, l.risque].filter(Boolean).join(' · '),
        ),
    },
  ]
}

function colonnes(preparer: (id: number) => void, role: Role): Colonne<LignePlan>[] {
  return [...colonnes1(preparer, role), ...colonnes2(), ...colonnes3()]
}

const FILTRES: Filtre<LignePlan>[] = [
  { cle: 'statut', libelle: 'Statut', valeur: (l) => statut('stock', cleStock(l.statut)).libelle },
  { cle: 'priorite', libelle: 'Priorité', valeur: (l) => libelleTier(l.tier) },
  { cle: 'abc', libelle: 'Classe ABC', valeur: (l) => l.classe_abc || VIDE },
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
]

export function OngletReferences({
  lignes,
  etat,
  role,
  onPreparer,
}: {
  lignes: readonly LignePlan[]
  etat: EtatTable
  role: Role
  onPreparer: (fournisseurId: number) => void
}) {
  return (
    <Carte titre={<span title={AIDE}>{TITRE}</span>} serre remplir className={styles.carteListe}>
      <DataTable<LignePlan>
        libelle="Références à commander"
        lignes={lignes}
        colonnes={colonnes(onPreparer, role)}
        filtres={FILTRES}
        cle={(l) => l.matiere_id ?? l.reference}
        recherche={etat.recherche}
        choix={etat.choix}
        placeholder="Référence, désignation, fournisseur, statut, tier…"
        exporter={{ route: '/export/plan-achat', parametres: { onglet: 'references' } }}
        vide="Rien à commander aujourd’hui."
      />
    </Carte>
  )
}
