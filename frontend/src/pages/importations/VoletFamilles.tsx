/**
 * Fiche dossier › Par famille de fil (ECRANS-PRO 5.7) : une ligne par famille (composition + façon
 * + titrage), triée par poids, pied « Tout le dossier » ; une ligne ouvre les marchandises de sa
 * famille. Un dossier vide dit où trouver sa marchandise, avec des liens vers les seuls onglets
 * présents (anomalie 5.1).
 */
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { kg, montant, nombre, part, prix, VIDE } from '../../lib/format'
import styles from './Importations.module.css'
import type { DossierFiche, Famille, Volet } from './types'

const COLONNES: Colonne<Famille>[] = [
  { cle: 'famille', titre: 'Famille de fil', rendu: (f) => <strong>{f.famille}</strong> },
  { cle: 'references', titre: 'Références', droite: true },
  { cle: 'lots', titre: 'Lots', droite: true, aide: 'Les lots distincts' },
  { cle: 'quantite', titre: 'Poids', droite: true, unite: 'kg', rendu: (f) => kg(f.quantite) },
  { cle: 'valeur_mad', titre: 'Achat MAD', droite: true, rendu: (f) => montant(f.valeur_mad, 'MAD') },
  {
    cle: 'charges_mad',
    titre: 'Charges hors TVA',
    aide: 'toutes les charges sauf la TVA',
    droite: true,
    rendu: (f) => montant(f.charges_mad, 'MAD'),
  },
  {
    cle: 'revient_mad',
    titre: 'Coût hors TVA',
    droite: true,
    rendu: (f) => <strong>{montant(f.revient_mad, 'MAD')}</strong>,
  },
  { cle: 'valeur_kg', titre: 'Achat / kg', droite: true, rendu: (f) => `${prix(f.valeur_kg)} MAD` },
  {
    cle: 'revient_kg',
    titre: 'Coût hors TVA / kg',
    droite: true,
    rendu: (f) => <strong>{prix(f.revient_kg)} MAD</strong>,
  },
  {
    cle: 'surcout',
    titre: 'Charges / achat',
    droite: true,
    rendu: (f) => (f.valeur_mad ? part(f.surcout) : VIDE),
  },
]

/** Le pied « Tout le dossier ». */
function Pied({ d }: { d: DossierFiche }) {
  const lots = new Set(d.lignes.map((l) => l.lot_id ?? `l${l.id}`)).size
  return (
    <tr>
      <td>Tout le dossier</td>
      <td className={styles.chiffre}>{nombre(new Set(d.lignes.map((l) => l.matiere_id)).size)}</td>
      <td className={styles.chiffre}>{nombre(lots)}</td>
      <td className={styles.chiffre}>{kg(d.poids)}</td>
      <td className={styles.chiffre}>{montant(d.marchandise_mad, 'MAD')}</td>
      <td className={styles.chiffre}>{montant(d.charges_mad, 'MAD')}</td>
      <td className={styles.chiffre}>{montant(d.revient_mad, 'MAD')}</td>
      <td className={styles.chiffre}>{d.poids ? `${prix(d.marchandise_mad / d.poids)} MAD` : VIDE}</td>
      <td className={styles.chiffre}>{d.revient_kg != null ? `${prix(d.revient_kg)} MAD` : VIDE}</td>
      <td className={styles.chiffre}>{d.marchandise_mad ? part(d.surcout) : VIDE}</td>
    </tr>
  )
}

export function VoletFamilles({
  d,
  presents,
  choisir,
}: {
  d: DossierFiche
  presents: readonly Volet[]
  choisir: (v: Volet, q?: string) => void
}) {
  if (!d.familles.length) {
    return (
      <Vide>
        Le dossier n’a pas encore de marchandise.{' '}
        {presents.includes('facture') ? (
          <Bouton taille="petit" variante="fantome" onClick={() => choisir('facture')}>
            Second camion de la facture
          </Bouton>
        ) : null}
        {presents.includes('main') ? (
          <Bouton taille="petit" variante="fantome" onClick={() => choisir('main')}>
            Saisie à la main
          </Bouton>
        ) : null}
        {!presents.includes('facture') && !presents.includes('main') && !d.a_la_main ? (
          <span className={styles.note}>
            Sa marchandise a été détachée : elle revient par sa facture (Importations › En attente).
          </span>
        ) : null}
      </Vide>
    )
  }
  return (
    <DataTable
      libelle="Par famille de fil"
      lignes={[...d.familles].sort((a, b) => b.quantite - a.quantite)}
      colonnes={COLONNES}
      cle={(f) => f.famille}
      recherche={false}
      cliquable={(f) => choisir('marchandises', f.famille)}
      pied={<Pied d={d} />}
      hauteur="fenetre"
    />
  )
}
