/**
 * Les colonnes de la liste des opérations (ECRANS-PRO partie 6) : numéro (ou « Brouillon », et
 * « sera refusée » avec ses raisons), date, motif / fournisseur / ordre selon l'onglet, lots,
 * quantité, valeur d'une ouverture par devise (qui voit les prix), état, auteurs.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { date, horodatage, kg, montants, nombre, nombreSigne, VIDE } from '../../lib/format'
import styles from './Operations.module.css'
import type { OperationFiche, TypeOperation } from './types'

type C = Colonne<OperationFiche>

const numero: C = {
  cle: 'numero',
  titre: 'Numéro',
  valeur: (o) => o.numero ?? 'Brouillon',
  rendu: (o) => (
    <span className={styles.valeur}>
      <strong className={styles.numero}>{o.numero ?? 'Brouillon'}</strong>
      {o.blocages.length ? (
        <span className={styles.refus} title={o.blocages.join(' ; ')}>
          sera refusée
        </span>
      ) : null}
    </span>
  ),
}

const jour: C = { cle: 'date', titre: 'Date', valeur: (o) => o.date, rendu: (o) => date(o.date) }

const motifTexte = (o: OperationFiche) => (o.code_motif ? `${o.code_motif} · ${o.motif}` : o.motif)

function motif(type: TypeOperation, permis: (adresse: string) => boolean): C {
  if (type === 'retour_fournisseur')
    return {
      cle: 'fournisseur',
      titre: 'Fournisseur',
      valeur: (o) => o.fournisseur,
      recherche: (o) => [o.motif, o.commentaire],
      rendu: (o) => (
        <span className={styles.valeur}>
          <span>{o.fournisseur || VIDE}</span>
          <span className={styles.note}>{[motifTexte(o), o.commentaire].filter(Boolean).join(' · ')}</span>
        </span>
      ),
    }
  if (type === 'retour_machine')
    return {
      cle: 'ordre',
      titre: 'Ordre',
      valeur: (o) => o.ordre,
      recherche: (o) => [o.motif, o.commentaire],
      rendu: (o) => (
        <span className={styles.valeur}>
          {o.ordre_id && permis(`/ordres/${o.ordre_id}`) ? (
            <Link to={`/ordres/${o.ordre_id}`} onClick={(e) => e.stopPropagation()}>
              {o.ordre}
            </Link>
          ) : (
            <span>{o.ordre || VIDE}</span>
          )}
          <span className={styles.note}>{[motifTexte(o), o.commentaire].filter(Boolean).join(' · ')}</span>
        </span>
      ),
    }
  return {
    cle: 'motif',
    titre: 'Motif',
    valeur: (o) => motifTexte(o),
    recherche: (o) => [o.commentaire],
    rendu: (o) => (
      <span className={styles.valeur}>
        <span>{motifTexte(o) || VIDE}</span>
        {o.commentaire ? <span className={styles.note}>{o.commentaire}</span> : null}
      </span>
    ),
  }
}

/** « RÉF · lot X · MAG[ → VERS] », deux premières lignes, puis « + N autre(s) ». */
const lots: C = {
  cle: 'lots',
  titre: 'Lots',
  valeur: (o) => o.lignes.map((l) => `${l.reference} ${l.lot}`).join(' '),
  rendu: (o) => (
    <span className={styles.valeur}>
      {o.lignes.slice(0, 2).map((l) => (
        <span key={l.id}>
          {l.reference} · lot {l.lot} · {l.magasin}
          {l.magasin_destination ? ` → ${l.magasin_destination}` : ''}
        </span>
      ))}
      {o.lignes.length > 2 ? (
        <span className={styles.note}>+ {nombre(o.lignes.length - 2)} autre(s)</span>
      ) : null}
    </span>
  ),
}

function quantite(type: TypeOperation): C {
  return {
    cle: 'quantite',
    titre: 'Quantité',
    droite: true,
    unite: 'kg',
    valeur: (o) => o.total,
    rendu: (o) => (type === 'ajustement' ? `${nombreSigne(o.total, 0, 2)} kg` : kg(o.total)),
  }
}

const valeur: C = {
  cle: 'valeur',
  titre: 'Valeur',
  droite: true,
  rendu: (o) => montants(Object.fromEntries((o.valeurs ?? []).map((v) => [v.devise, v.montant ?? 0]))),
}

const etat: C = {
  cle: 'statut',
  titre: 'État',
  rendu: (o) => <Badge famille="document" valeur={o.statut} />,
}

/** « {créé par}[ · validée par {nom}][ · annulée par {nom} le {date}] ». */
export function parDe(o: OperationFiche): string {
  const morceaux = [o.cree_par]
  if (o.validee_par) morceaux.push(`validée par ${o.validee_par}`)
  if (o.annulee_le) morceaux.push(`annulée par ${o.annulee_par} le ${horodatage(o.annulee_le)}`)
  return morceaux.filter(Boolean).join(' · ')
}

const par: C = { cle: 'par', titre: 'Par', valeur: parDe }

export function colonnesOperations(
  type: TypeOperation,
  voitPrix: boolean,
  permis: (adresse: string) => boolean,
): C[] {
  const prix = type === 'ouverture' && voitPrix ? [valeur] : []
  return [numero, jour, motif(type, permis), lots, quantite(type), ...prix, etat, par]
}
