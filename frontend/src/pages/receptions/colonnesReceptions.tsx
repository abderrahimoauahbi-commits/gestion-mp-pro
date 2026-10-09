/**
 * Les colonnes de la liste des réceptions (ECRANS-PRO 4.15) : n° ou « Brouillon », les bons en
 * liens, la facture (ou « à compléter »), le pesé hors refus, le statut et ce qui reste à régler
 * avant la validation (les blocages du serveur en infobulle).
 */
import { Link } from 'react-router'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { date, nombre, VIDE } from '../../lib/format'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import type { ReceptionResume } from './types'

function Bons({ r }: { r: ReceptionResume }) {
  if (!r.commandes.length) return <span className={styles.note}>hors commande</span>
  return (
    <span className={styles.rangeeCentree}>
      {r.commandes.map((c) => (
        <Link key={c.id} to={`/commandes/${c.id}`} onClick={(e) => e.stopPropagation()}>
          {c.numero}
        </Link>
      ))}
    </span>
  )
}

function Geste({ r, corriger }: { r: ReceptionResume; corriger: (r: ReceptionResume) => void }) {
  if (r.statut === 'brouillon')
    return (
      <Bouton taille="petit" titre="Rouvre la saisie de ce brouillon" onClick={() => corriger(r)}>
        Corriger
      </Bouton>
    )
  if (r.statut === 'validee' && r.lots.length)
    return (
      <BoutonImprimer
        route="/documents/etiquettes"
        parametres={{ lots: r.lots.join(',') }}
        libelle="Étiquettes"
        titre="Les étiquettes QR des lots de cette réception"
      />
    )
  if (r.statut === 'validee')
    return (
      <Bouton taille="petit" grise="Aucun lot (tout refusé).">
        Étiquettes
      </Bouton>
    )
  return null
}

function colonnesReceptions1(_corriger: (r: ReceptionResume) => void): Colonne<ReceptionResume>[] {
  return [
    {
      cle: 'numero',
      titre: 'N°',
      valeur: (r) => r.numero ?? 'Brouillon',
      rendu: (r) =>
        r.numero ? (
          <span className={styles.fort}>{r.numero}</span>
        ) : (
          <Badge famille="document" valeur="brouillon" />
        ),
    },
    { cle: 'date', titre: 'Arrivée', rendu: (r) => date(r.date) },
    {
      cle: 'fournisseur',
      titre: 'Fournisseur',
      rendu: (r) =>
        deux(
          <span className={styles.fort}>{r.fournisseur}</span>,
          [r.cree_par ? `par ${r.cree_par}` : '', r.controle_par ? `contrôlé par ${r.controle_par}` : '']
            .filter(Boolean)
            .join(' · ') || null,
        ),
    },
    {
      cle: 'commandes',
      titre: 'Bon(s) de commande',
      valeur: (r) => r.commandes.map((c) => c.numero).join(' '),
      rendu: (r) => <Bons r={r} />,
    },
    {
      cle: 'numero_bl',
      titre: 'N° du BL',
      valeur: (r) => r.numero_bl || VIDE,
      rendu: (r) => <span className={styles.sansCoupure}>{r.numero_bl || VIDE}</span>,
    },
    {
      cle: 'facture',
      titre: 'Facture',
      valeur: (r) => r.facture?.numero ?? '',
      rendu: (r) =>
        r.facture?.numero ? (
          <span className={styles.sansCoupure}>{r.facture.numero}</span>
        ) : (
          <span className={styles.note}>à compléter</span>
        ),
    },
    { cle: 'nb_lignes', titre: 'Lignes', droite: true },
  ]
}

function colonnesReceptions2(corriger: (r: ReceptionResume) => void): Colonne<ReceptionResume>[] {
  return [
    {
      cle: 'pese',
      titre: 'Pesé (kg)',
      aide: 'Hors lignes refusées',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (r) => nombre(r.pese),
    },
    {
      cle: 'statut',
      titre: 'Statut',
      valeur: (r) => statut('document', r.statut).libelle,
      rendu: (r) =>
        deux(
          <Badge famille="document" valeur={r.statut} />,
          r.blocages.length ? (
            <span title={r.blocages.join('\n')}>{nombre(r.blocages.length)} point(s) à régler</span>
          ) : null,
        ),
    },
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (r) => (
        <span onClick={(e) => e.stopPropagation()}>
          <Geste r={r} corriger={corriger} />
        </span>
      ),
    },
  ]
}

export function colonnesReceptions(corriger: (r: ReceptionResume) => void): Colonne<ReceptionResume>[] {
  return [...colonnesReceptions1(corriger), ...colonnesReceptions2(corriger)]
}

/** Les champs cherchés sans être affichés. */
export const CHERCHES = (r: ReceptionResume) => [
  r.numero ?? 'Brouillon',
  r.cree_par,
  r.controle_par,
  r.validee_par,
  r.observations,
  r.devise,
  r.annulation_motif,
]

export function filtresReceptions(noms: ReadonlyMap<string, string>): Filtre<ReceptionResume>[] {
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (r) => String(r.fournisseur_id),
      libelleValeur: (v) => noms.get(v) ?? v,
    },
    { cle: 'origine', libelle: 'Bon', valeur: (r) => (r.commandes.length ? 'Sur bon' : 'Hors commande') },
    {
      cle: 'facture',
      libelle: 'Facture',
      valeur: (r) => (r.facture?.numero ? 'Avec facture' : 'À compléter'),
    },
    {
      cle: 'qualite',
      libelle: 'Qualité',
      valeur: (r) => (r.nb_refus ? 'Avec refus' : r.nb_reserve ? 'Avec réserve' : 'Tout conforme'),
    },
  ]
}
