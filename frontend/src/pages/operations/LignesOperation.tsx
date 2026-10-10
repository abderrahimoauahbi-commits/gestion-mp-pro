/**
 * Les lignes d'une opération (ECRANS-PRO partie 6) : référence, lot (lien vers sa fiche, ou « créé
 * à la validation »), magasins, quantité (signée et colorée pour un ajustement), prix au kilo et
 * valeur d'une ouverture (qui voit les prix), « Modifier » / « Retirer » tant que c'est modifiable.
 * Une ligne que le motif rend impossible est dite en rouge (an. 2). Pied de totaux.
 */
import { classes } from '../../composants/mise-en-page/classes'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { kgEtMetres, montant, nombreSigne, prixUnite, VIDE } from '../../lib/format'
import styles from './Operations.module.css'
import { incompatibilite, type LigneSaisie } from './saisie'
import type { MotifLu, TypeOperation } from './types'

type C = Colonne<LigneSaisie>

export interface LignesProps {
  type: TypeOperation
  motif: MotifLu | undefined
  lignes: readonly LigneSaisie[]
  modifiable: boolean
  voitPrix: boolean
  enCours: string | null
  modifier: (l: LigneSaisie) => void
  retirer: (l: LigneSaisie) => void
}

function lot(p: LignesProps): C {
  return {
    cle: 'lot',
    titre: 'Lot',
    valeur: (l) => l.lot,
    lien: (l) => (l.lot_id ? `/lots/${l.lot_id}` : null),
    rendu: (l) => (
      <span className={styles.valeur}>
        <span className="mono">
          {l.lot_interne && !l.lot_id ? 'LOT-… donné à la validation' : l.lot || VIDE}
        </span>
        {!l.lot_id && !l.lot_interne ? <span className={styles.note}>lot créé à la validation</span> : null}
        {incompatibilite(l, p.type, p.motif) ? (
          <span className={styles.refus}>{incompatibilite(l, p.type, p.motif)}</span>
        ) : null}
      </span>
    ),
  }
}

function quantite(type: TypeOperation): C {
  return {
    cle: 'quantite',
    titre: type === 'ajustement' ? 'Ajustement' : 'Quantité',
    droite: true,
    unite: 'kg',
    total: true,
    valeur: (l) => l.quantite,
    rendu: (l) =>
      type === 'ajustement' ? (
        <span className={classes('nombre', l.quantite < 0 ? styles.negatif : styles.positif)}>
          {nombreSigne(l.quantite, 0, 2)}&nbsp;kg
        </span>
      ) : (
        <span className="nombre">{kgEtMetres(l.quantite, l.kg_par_ml)}</span>
      ),
  }
}

const prixKg: C = {
  cle: 'prix',
  titre: 'Prix / kg',
  droite: true,
  rendu: (l) => prixUnite(l.prix, l.devise, 'kg'),
}

const valeur: C = {
  cle: 'valeur',
  titre: 'Valeur',
  droite: true,
  unite: (l) => l.devise,
  total: true,
  valeur: (l) => l.prix * l.quantite,
  rendu: (l) => montant(l.prix * l.quantite, l.devise),
}

function gestes(p: LignesProps): C {
  return {
    cle: 'gestes',
    titre: '',
    triable: false,
    exporte: false,
    rendu: (l) => (
      <span className={styles.gestesLigne}>
        <Bouton
          taille="petit"
          onClick={() => p.modifier(l)}
          grise={p.enCours ? 'Une ligne est déjà en cours de saisie' : undefined}
        >
          Modifier
        </Bouton>
        <Bouton
          taille="petit"
          variante="fantome"
          onClick={() => p.retirer(l)}
          titre={`Retirer la ligne ${l.reference}`}
        >
          Retirer
        </Bouton>
      </span>
    ),
  }
}

export function colonnesLignes(p: LignesProps): C[] {
  const ouverture = p.type === 'ouverture'
  return [
    { cle: 'reference', titre: 'Référence', rendu: (l) => <strong>{l.reference}</strong> },
    lot(p),
    { cle: 'magasin', titre: p.type === 'transfert' ? 'De' : 'Magasin' },
    ...(p.type === 'transfert' ? [{ cle: 'magasin_destination', titre: 'Vers' }] : []),
    quantite(p.type),
    ...(ouverture && p.voitPrix ? [prixKg, valeur] : []),
    ...(p.modifiable ? [gestes(p)] : []),
  ]
}

export function LignesOperation(p: LignesProps) {
  return (
    <DataTable
      libelle="Lignes de l’opération"
      lignes={p.lignes}
      colonnes={colonnesLignes(p)}
      cle={(l) => l.cle}
      recherche={false}
      hauteur="fenetre"
      marquee={(l) => l.cle === p.enCours || Boolean(incompatibilite(l, p.type, p.motif))}
      vide={
        p.modifiable
          ? 'Aucune ligne. Remplir le formulaire au-dessus, puis « Ajouter la ligne ».'
          : 'Aucune ligne.'
      }
    />
  )
}
