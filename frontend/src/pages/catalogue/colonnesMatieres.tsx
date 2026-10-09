/**
 * Les colonnes de la liste des matières (ECRANS-PRO partie 7, « Onglet Matières ») et ses
 * filtres liés. La colonne « Prix » n'existe pas pour l'alimentation (R10) : ni « — », ni
 * colonne vide, rien.
 */
import type { ReactNode } from 'react'

import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { kg, metres, nombre, prixUnite, VIDE } from '../../lib/format'
import styles from './catalogue.module.css'
import type { Matiere } from './types'

/** « Palette · 1 080 kg », « au kilo ». */
export function conditionnementLisible(m: Matiere): string {
  const c = m.conditionnement
  return c.unite === 'kg' ? 'au kilo' : `${c.unite} · ${kg(c.contenance)}`
}

/** Le détail du conditionnement : « bobine 12,5 kg × 96 · mini 500 kg · déduit ». */
function detailConditionnement(m: Matiere): string {
  const parties: string[] = []
  if (m.poids_bobine) {
    parties.push(`bobine ${kg(m.poids_bobine)}${m.bobines_palette ? ` × ${nombre(m.bobines_palette)}` : ''}`)
  }
  if (m.minimum_commande) parties.push(`mini ${kg(m.minimum_commande)}`)
  if (m.conditionnement.unite !== 'kg' && !m.conditionnement.declare) parties.push('déduit')
  return parties.join(' · ')
}

/** Le prix tel qu'on l'achète, et pour un prix au mètre son équivalent au kilo. */
export function PrixMatiere({ m }: { m: Matiere }) {
  if (!m.prix || !m.devise) return <>{VIDE}</>
  const unite = m.unite_prix ?? 'kg'
  return (
    <>
      {prixUnite(m.prix, m.devise, unite)}
      {unite === 'ml' && m.prix_kg ? (
        <span className={styles.dessous}>soit {prixUnite(m.prix_kg, m.devise, 'kg')}</span>
      ) : null}
    </>
  )
}

function Reference({ m }: { m: Matiere }) {
  return (
    <>
      <span className={m.actif ? styles.code : `${styles.code} ${styles.eteinte}`}>{m.reference}</span>
      {m.actif ? null : (
        <>
          {' '}
          <Badge ton="neutre">désactivée</Badge>
        </>
      )}
      {m.designation ? (
        <span className={`${styles.dessous} ${styles.coupe}`} title={m.designation}>
          {m.designation}
        </span>
      ) : null}
    </>
  )
}

function Stock({ m }: { m: Matiere }) {
  const bas = m.actif && m.stock_min > 0 && m.stock < m.stock_min
  return (
    <>
      {kg(m.stock)}
      {m.lineaire && m.kg_par_ml ? (
        <span className={styles.dessous}>{metres(m.stock, m.kg_par_ml)}</span>
      ) : null}
      {bas ? (
        <span className={styles.dessous}>
          <Badge ton="attention" titre="Sous le stock minimum">
            sous le minimum
          </Badge>
        </span>
      ) : null}
    </>
  )
}

/** Une valeur, et son détail dessous (s'il y en a un). */
export function deux(haut: ReactNode, bas?: ReactNode) {
  return (
    <>
      {haut}
      {bas ? <span className={styles.dessous}>{bas}</span> : null}
    </>
  )
}

const COLONNES_CLASSE: readonly Colonne<Matiere>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    rendu: (m) => <Reference m={m} />,
    recherche: (m) => [m.designation, m.couleur_code, m.groupe_equiv, m.code_douanier],
    largeur: 220,
  },
  { cle: 'role', titre: 'Rôle' },
  {
    cle: 'fournisseur',
    titre: 'Fournisseur',
    rendu: (m) => m.fournisseur ?? <Badge ton="attention">aucun</Badge>,
  },
  {
    cle: 'composition',
    titre: 'Composition',
    recherche: (m) => [m.composition_libelle],
    rendu: (m) =>
      deux(m.composition ?? VIDE, m.composition_libelle !== m.composition ? m.composition_libelle : null),
  },
  {
    cle: 'type_fil',
    titre: 'Type',
    aide: 'Type de fil, et titrage dessous',
    recherche: (m) => [m.titrage, m.titrage_unite],
    rendu: (m) => deux(m.type_fil ?? VIDE, m.titrage),
  },
  {
    cle: 'couleur',
    titre: 'Couleur',
    aide: 'Couleur de la classification ; code couleur du fournisseur dessous',
    recherche: (m) => [m.couleur_libelle],
    rendu: (m) => deux(m.couleur ?? VIDE, m.couleur_code),
  },
]

const COLONNE_PRIX: Colonne<Matiere> = {
  cle: 'prix',
  titre: 'Prix',
  droite: true,
  valeur: (m) => m.prix_kg ?? m.prix,
  rendu: (m) => <PrixMatiere m={m} />,
}

const COLONNES_STOCK: readonly Colonne<Matiere>[] = [
  {
    cle: 'stock_min',
    titre: 'Stock min.',
    aide: 'Stock minimum, et couverture minimum (mois de consommation) dessous',
    droite: true,
    rendu: (m) =>
      deux(
        m.stock_min ? kg(m.stock_min) : VIDE,
        m.couv_min_mois ? `${nombre(m.couv_min_mois, 0, 1)} mois` : null,
      ),
  },
  {
    cle: 'conditionnement',
    titre: 'Conditionnement',
    valeur: (m) => conditionnementLisible(m),
    rendu: (m) =>
      deux(
        m.conditionnement.unite === 'kg' ? (
          'au kilo'
        ) : (
          <Badge ton={m.conditionnement.declare ? 'accent' : 'neutre'}>{conditionnementLisible(m)}</Badge>
        ),
        detailConditionnement(m),
      ),
  },
  { cle: 'groupe_equiv', titre: 'Groupe' },
  { cle: 'stock', titre: 'En stock', droite: true, unite: 'kg', total: true, rendu: (m) => <Stock m={m} /> },
]

/** Les colonnes ; `voitPrix` : direction et achats (sans lui, pas de colonne « Prix » du tout). */
export function colonnesMatieres(voitPrix: boolean): Colonne<Matiere>[] {
  return [...COLONNES_CLASSE, ...(voitPrix ? [COLONNE_PRIX] : []), ...COLONNES_STOCK]
}

/** Les sept filtres liés ; rôle et fournisseur par identifiant (l'export du serveur les lit). */
export function filtresMatieres(lignes: readonly Matiere[]): Filtre<Matiere>[] {
  const roles = new Map(lignes.map((m) => [String(m.role_id), m.role]))
  const fournisseurs = new Map(lignes.map((m) => [String(m.fournisseur_id ?? ''), m.fournisseur ?? '']))
  return [
    {
      cle: 'role',
      libelle: 'Rôle',
      valeur: (m) => String(m.role_id),
      libelleValeur: (v) => roles.get(v) ?? v,
    },
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (m) => (m.fournisseur_id == null ? null : String(m.fournisseur_id)),
      libelleValeur: (v) => fournisseurs.get(v) || `n° ${v}`,
    },
    {
      cle: 'composition',
      libelle: 'Composition',
      valeur: (m) => m.composition,
      libelleValeur: (v) => {
        const l = lignes.find((m) => m.composition === v)?.composition_libelle
        return l && l !== v ? `${v} — ${l}` : v
      },
    },
    { cle: 'type', libelle: 'Type de fil', valeur: (m) => m.type_fil },
    { cle: 'couleur', libelle: 'Couleur', valeur: (m) => m.couleur },
    { cle: 'titrage', libelle: 'Titrage', valeur: (m) => m.titrage },
    { cle: 'unite_titrage', libelle: 'Unité du titrage', valeur: (m) => m.titrage_unite },
  ]
}
