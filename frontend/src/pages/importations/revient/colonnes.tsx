/**
 * Les colonnes des vues « Regroupé » (ECRANS-PRO 5.16) et « Lot par lot » (5.17), et leur pied
 * « Total » tiré des totaux du serveur (le coût au kilo du total est recalculé, il ne s'additionne
 * pas). Tous les montants sont en MAD (la marchandise est déjà convertie au cours payé) : jamais
 * deux devises dans une colonne.
 */
import { Badge } from '../../../composants/retour/Badge'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { date, kg, montant, nombre, part, VIDE } from '../../../lib/format'
import type { Schema } from '../../../lib/types'
import { Dossiers, LienDossier, LienMatiere, type Liens } from './liens'
import styles from './revient.module.css'

export type Analyse = Schema<'AnalyseRevient'>
export type Groupe = Schema<'GroupeRevient'>
/** Une ligne « lot par lot », numérotée (deux lignes peuvent se ressembler en tout). */
export type LigneLot = Schema<'LigneDetailRevient'> & { n: number }

/** Les grandeurs communes à un groupe et à une ligne de lot. */
type Chiffres = Pick<Groupe, 'poids' | 'marchandise_mad' | 'charges_mad' | 'revient_mad' | 'tva_mad'> & {
  decaisse_mad: number
  surcout: number
  revient_kg: number
}

const mad = (v: number) => montant(v, 'MAD')

/** Poids · Achat MAD · Charges hors TVA · Coût hors TVA · Coût hors TVA / kg · TVA · Coût TTC. */
export function colonnesChiffres<T extends Chiffres>(achatKg: (l: T) => number): Colonne<T>[] {
  return [
    { cle: 'poids', titre: 'Poids', droite: true, rendu: (l) => kg(l.poids) },
    { cle: 'marchandise_mad', titre: 'Achat MAD', droite: true, rendu: (l) => mad(l.marchandise_mad) },
    {
      cle: 'charges_mad',
      titre: 'Charges hors TVA',
      aide: 'toutes les charges sauf la TVA',
      droite: true,
      rendu: (l) => <span title={`${part(l.surcout)} de l’achat`}>{mad(l.charges_mad)}</span>,
    },
    {
      cle: 'revient_mad',
      titre: 'Coût hors TVA',
      aide: 'achat + charges hors TVA',
      droite: true,
      rendu: (l) => <strong>{mad(l.revient_mad)}</strong>,
    },
    {
      cle: 'revient_kg',
      titre: 'Coût hors TVA / kg',
      aide: 'en MAD par kilo ; dessous, l’achat au kilo',
      droite: true,
      rendu: (l) => (
        <span className={styles.pile}>
          <strong>{nombre(l.revient_kg, 2)}</strong>
          <span className={styles.note}>achat {nombre(achatKg(l), 2)}</span>
        </span>
      ),
    },
    {
      cle: 'tva_mad',
      titre: 'TVA',
      droite: true,
      rendu: (l) => <span className={styles.note}>{mad(l.tva_mad)}</span>,
    },
    {
      cle: 'decaisse_mad',
      titre: 'Coût TTC',
      droite: true,
      rendu: (l) => <span className={styles.note}>{mad(l.decaisse_mad)}</span>,
    },
  ]
}

/** Les colonnes de la vue « Regroupé » : l'axe, les lots, les chiffres, les dossiers. */
export function colonnesGroupe(libelleAxe: string, liens: Liens): Colonne<Groupe>[] {
  return [
    {
      cle: 'valeur',
      titre: libelleAxe,
      rendu: (g) => <strong title={g.valeur}>{g.valeur || VIDE}</strong>,
    },
    { cle: 'lignes', titre: 'Lots', aide: 'lots distincts', droite: true, rendu: (g) => nombre(g.lignes) },
    ...colonnesChiffres<Groupe>((g) => g.marchandise_kg),
    {
      cle: 'dossiers',
      titre: 'Dossiers',
      triable: false,
      valeur: (g) => g.dossiers.join(' '),
      rendu: (g) => <Dossiers numeros={g.dossiers} liens={liens} />,
    },
  ]
}

/** Les colonnes de la vue « Lot par lot ». */
export function colonnesLots(liens: Liens): Colonne<LigneLot>[] {
  return [
    {
      cle: 'dossier',
      titre: 'Dossier',
      rendu: (l) => (
        <span className={styles.dossiers}>
          <LienDossier numero={l.dossier} liens={liens} />
          {l.statut.toLowerCase() === 'ouvert' ? <Badge famille="dossier" valeur="ouvert" /> : null}
        </span>
      ),
    },
    { cle: 'date_arrivee', titre: 'Arrivée', rendu: (l) => date(l.date_arrivee) },
    {
      cle: 'reference',
      titre: 'Référence',
      rendu: (l) => <LienMatiere reference={l.reference} liens={liens} />,
    },
    { cle: 'lot_fournisseur', titre: 'Lot', rendu: (l) => l.lot_fournisseur || VIDE },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    {
      cle: 'titrage',
      titre: 'Titrage',
      rendu: (l) => <span className={styles.note}>{l.titrage || VIDE}</span>,
    },
    ...colonnesChiffres<LigneLot>((l) => l.valeur_unite),
  ]
}

/** Les cellules chiffrées du pied « Total ». */
function CellulesTotal({ r }: { r: Analyse }) {
  return (
    <>
      <td className={styles.droite}>{kg(r.total_poids)}</td>
      <td className={styles.droite}>{mad(r.total_marchandise_mad)}</td>
      <td className={styles.droite}>{mad(r.total_charges_mad)}</td>
      <td className={styles.droite}>{mad(r.total_revient_mad)}</td>
      <td className={styles.droite}>
        {r.total_poids ? nombre(r.total_revient_mad / r.total_poids, 2) : VIDE}
      </td>
      <td className={styles.droite}>{mad(r.total_tva_mad)}</td>
      <td className={styles.droite}>{mad(r.total_decaisse_mad)}</td>
    </>
  )
}

/** Le pied « Total » de la vue « Regroupé » (plus d'une ligne). */
export function PiedGroupe({ r }: { r: Analyse }) {
  return (
    <tr>
      <td>Total</td>
      <td className={styles.droite}>{nombre(r.total_lignes)}</td>
      <CellulesTotal r={r} />
      <td />
    </tr>
  )
}

/** Le pied « Total » de la vue « Lot par lot ». */
export function PiedLots({ r }: { r: Analyse }) {
  return (
    <tr>
      <td colSpan={6}>Total</td>
      <CellulesTotal r={r} />
    </tr>
  )
}
