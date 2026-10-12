/**
 * Les colonnes de la liste des dossiers (ECRANS-PRO 5.2) : numéro et « à vérifier » (les alertes du
 * serveur, toutes), arrivée (clos le, annulé le et motif), facture et réceptions en liens, familles
 * de fil, poids, achat, charges hors TVA (part de l'achat, non répartis à part), coût hors TVA (au
 * kilo), coût TTC (dont TVA).
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { date, horodatage, kg, montant, montantPrecis, nombre, part, prix, VIDE } from '../../lib/format'
import styles from './Importations.module.css'
import { partCharges, type DossierResume } from './types'

type C = Colonne<DossierResume>

/** Un lien dans une ligne cliquable : le clic ne rouvre pas la ligne. */
const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

const dossier: C = {
  cle: 'numero',
  titre: 'Dossier',
  valeur: (d) => d.numero,
  recherche: (d) => [d.libelle, d.banque, d.commentaire, d.annulation_motif],
  rendu: (d) => (
    <span className={styles.valeur}>
      <span className={styles.rangee}>
        <strong>{d.numero}</strong>
        {d.a_verifier.length ? (
          <Badge ton="critique" titre={d.a_verifier.join(' ; ')}>
            à vérifier
          </Badge>
        ) : null}
      </span>
      {d.libelle ? (
        <span className={`${styles.note} ${styles.coupe}`} title={d.libelle}>
          {d.libelle}
        </span>
      ) : null}
    </span>
  ),
}

const arrivee: C = { cle: 'date_arrivee', titre: 'Arrivée', rendu: (d) => date(d.date_arrivee) }

const closLe: C = {
  cle: 'clos_le',
  titre: 'Clos le',
  rendu: (d) => (d.clos_le ? horodatage(d.clos_le) : VIDE),
}

const annuleLe: C = {
  cle: 'annule_le',
  titre: 'Annulé le',
  rendu: (d) => (
    <span className={styles.valeur}>
      <span>{d.annule_le ? horodatage(d.annule_le) : VIDE}</span>
      {d.annule_par ? <span className={styles.note}>par {d.annule_par}</span> : null}
    </span>
  ),
}

const motif: C = { cle: 'annulation_motif', titre: 'Motif' }

/** « Facture F · REC-… · REC-… », chaque réception vers sa fiche ; « saisi à la main ». */
function FacturesEtReceptions({ d }: { d: DossierResume }) {
  if (d.a_la_main && !d.receptions.length) return <span className={styles.note}>saisi à la main</span>
  if (!d.pieces.length) return <>{VIDE}</>
  const ids = new Map(d.receptions.map((r) => [r.numero, r.id]))
  return (
    <span className={styles.valeur}>
      {d.pieces.map((p) => (
        <span key={p.facture ?? 'sans'} className={styles.liens}>
          <strong>{p.facture ?? 'sans facture'}</strong>
          {p.receptions.map((numero) => {
            const id = ids.get(numero)
            return id ? (
              <Link key={numero} to={`/receptions/${id}`} onClick={arreter}>
                {numero}
              </Link>
            ) : (
              <span key={numero}>{numero}</span>
            )
          })}
        </span>
      ))}
    </span>
  )
}

const factures: C = {
  cle: 'factures',
  titre: 'Facture · réceptions',
  valeur: (d) => d.pieces.map((p) => p.facture ?? '').join(' '),
  recherche: (d) => [
    ...d.receptions.map((r) => r.numero),
    ...d.fournisseurs,
    ...d.factures.map((f) => f.fournisseur),
  ],
  rendu: (d) => <FacturesEtReceptions d={d} />,
}

const familles: C = {
  cle: 'familles',
  titre: 'Familles de fil',
  valeur: (d) => d.familles.map((f) => f.famille).join(' '),
  rendu: (d) => {
    if (!d.familles.length) return <span className={styles.note}>aucune marchandise</span>
    const triees = [...d.familles].sort((a, b) => b.quantite - a.quantite)
    return (
      <span className={styles.valeur}>
        {triees.slice(0, 3).map((f) => (
          <span key={f.famille}>
            {f.famille} · {kg(f.quantite)}
          </span>
        ))}
        {triees.length > 3 ? (
          <span className={styles.note}>+ {nombre(triees.length - 3)} autre(s)</span>
        ) : null}
      </span>
    )
  },
}

const poids: C = {
  cle: 'poids',
  titre: 'Poids',
  droite: true,
  unite: 'kg',
  total: true,
  rendu: (d) => kg(d.poids),
}

const achat: C = {
  cle: 'marchandise_mad',
  titre: 'Achat MAD',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (d) => montant(d.marchandise_mad, 'MAD'),
}

const charges: C = {
  cle: 'charges_mad',
  titre: 'Charges hors TVA',
  aide: 'toutes les charges sauf la TVA',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (d) => {
    const p = partCharges(d.charges_mad, d.marchandise_mad)
    return (
      <span className={styles.valeur}>
        <span>{montant(d.charges_mad, 'MAD')}</span>
        <span className={styles.note}>
          {p == null ? VIDE : `${part(p)} de l’achat`}
          {d.surcout_aberrant ? <span className={styles.rouge}> — à vérifier</span> : null}
        </span>
        {Math.abs(d.charges_non_reparties_mad) > 0.005 ? (
          <span className={styles.rouge} title="Frais sans marchandise où se répartir : dans aucun coût">
            + {montantPrecis(d.charges_non_reparties_mad, 'MAD')} non répartis
          </span>
        ) : null}
      </span>
    )
  },
}

const cout: C = {
  cle: 'revient_mad',
  titre: 'Coût hors TVA',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (d) => (
    <span className={styles.valeur}>
      <strong>{montant(d.revient_mad, 'MAD')}</strong>
      <span className={styles.note}>{d.revient_kg == null ? VIDE : `${prix(d.revient_kg)} MAD / kg`}</span>
    </span>
  ),
}

const ttc: C = {
  cle: 'decaisse_mad',
  titre: 'Coût TTC',
  droite: true,
  unite: 'MAD',
  total: true,
  rendu: (d) => (
    <span className={styles.valeur}>
      <span>{montant(d.decaisse_mad, 'MAD')}</span>
      {d.tva_mad ? <span className={styles.note}>dont TVA {montant(d.tva_mad, 'MAD')}</span> : null}
    </span>
  ),
}

/** Les colonnes d'un onglet : « Clos le » pour les clos, « Annulé le » et « Motif » pour les annulés. */
export function colonnesDossiers(statut: 'ouvert' | 'clos' | 'annule'): C[] {
  const etat = statut === 'clos' ? [closLe] : statut === 'annule' ? [annuleLe, motif] : []
  return [dossier, arrivee, ...etat, factures, familles, poids, achat, charges, cout, ttc]
}
