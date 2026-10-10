/**
 * Fiche réception › Lignes pesées (ECRANS-PRO 4.18) : chaque ligne avec son bon et son lot (liens
 * vers leurs fiches), le reste à livrer (brouillon) ou le reste après (validée), l'annonce, la
 * pesée et son écart, les bobines, le magasin, la qualité et le prix payé.
 */
import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { metres, nombre, partSignee, prixUnite, VIDE } from '../../lib/format'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import type { LigneReception, ReceptionFiche } from './types'

function Lot({ l, brouillon }: { l: LigneReception; brouillon: boolean }) {
  if (l.qualite === 'refuse') return <>{VIDE}</>
  if (l.lot_id) return <span className={styles.sansCoupure}>{l.lot_numero}</span>
  if (brouillon && l.lot_interne) return <Badge ton="neutre">lot interne</Badge>
  return <span className={styles.note}>{l.lot_numero || 'à saisir'}</span>
}

function colonnes1(r: ReceptionFiche): Colonne<LigneReception>[] {
  const brouillon = r.statut === 'brouillon'
  return [
    {
      cle: 'reference',
      titre: 'Référence · bon',
      lien: (l) => (l.commande_id ? `/commandes/${l.commande_id}` : null),
      rendu: (l) =>
        deux(
          <span className={styles.ref} title={`${l.reference} — ${l.designation}`}>
            {l.reference}
          </span>,
          l.commande ? `bon ${l.commande}` : 'hors commande',
        ),
    },
    {
      cle: 'lot',
      titre: 'Lot',
      aide: 'La fiche du lot : où il est, où il est allé',
      valeur: (l) => l.lot_numero,
      lien: (l) => (l.lot_id ? `/lots/${l.lot_id}` : null),
      rendu: (l) => <Lot l={l} brouillon={brouillon} />,
    },
    {
      cle: 'reste',
      titre: 'Reste (kg)',
      aide: brouillon
        ? 'Reste à livrer sur la ligne du bon'
        : 'Reste après cette réception sur la ligne du bon',
      droite: true,
      valeur: (l) => (l.commande_ligne_id ? (brouillon ? l.quantite_attendue : l.reste_apres) : null),
      rendu: (l) =>
        l.commande_ligne_id
          ? deux(
              nombre(brouillon ? l.quantite_attendue : l.reste_apres),
              l.deja_recu ? `déjà reçu ${nombre(l.deja_recu)}` : null,
            )
          : VIDE,
    },
  ]
}

function colonnes2(_r: ReceptionFiche): Colonne<LigneReception>[] {
  return [
    {
      cle: 'quantite_bl',
      titre: 'Annoncé BL (kg)',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (l) => (l.quantite_bl ? nombre(l.quantite_bl) : VIDE),
    },
    {
      cle: 'quantite_pesee',
      titre: 'Pesé (kg)',
      droite: true,
      unite: 'kg',
      total: true,
      valeur: (l) => (l.qualite === 'refuse' ? 0 : l.quantite_pesee),
      rendu: (l) =>
        deux(nombre(l.quantite_pesee), l.kg_par_ml ? metres(l.quantite_pesee, l.kg_par_ml) : null),
    },
    {
      cle: 'ecart',
      titre: 'Écart',
      droite: true,
      valeur: (l) => l.ecart_relatif,
      rendu: (l) =>
        l.ecart_relatif == null || l.ecart == null
          ? VIDE
          : deux(
              <Badge ton={l.hors_tolerance ? 'critique' : 'ok'}>{partSignee(l.ecart_relatif)}</Badge>,
              `${l.ecart > 0 ? '+' : ''}${nombre(l.ecart, 0, 2)} kg`,
            ),
    },
  ]
}

function colonnes3(r: ReceptionFiche): Colonne<LigneReception>[] {
  const tolBobine = r.tolerances?.poids_bobine ?? 0.05
  return [
    {
      cle: 'nb_bobines',
      titre: 'Bobines',
      droite: true,
      rendu: (l) =>
        l.nb_bobines
          ? deux(
              nombre(l.nb_bobines),
              l.nb_palettes ? `${nombre(l.nb_palettes, 0, 3)} pal. + ${nombre(l.bobines_en_plus)}` : null,
            )
          : VIDE,
    },
    {
      cle: 'poids_moyen_bobine',
      titre: 'kg / bobine',
      droite: true,
      rendu: (l) => {
        if (!l.poids_moyen_bobine) return VIDE
        const e = l.poids_bobine_catalogue ? l.poids_moyen_bobine / l.poids_bobine_catalogue - 1 : null
        const ton = e != null && Math.abs(e) > tolBobine ? 'attention' : 'ok'
        return deux(
          <Badge ton={ton}>{nombre(l.poids_moyen_bobine, 2)}</Badge>,
          l.poids_bobine_catalogue
            ? `catalogue ${nombre(l.poids_bobine_catalogue, 2)} (${partSignee(e)})`
            : null,
        )
      },
    },
    {
      cle: 'magasin',
      titre: 'Magasin',
      valeur: (l) => (l.qualite === 'refuse' ? 'n’entre pas' : l.magasin || 'à choisir'),
    },
    {
      cle: 'qualite',
      titre: 'Qualité',
      valeur: (l) => statut('qualite_reception', l.qualite).libelle,
      rendu: (l) => deux(<Badge famille="qualite_reception" valeur={l.qualite} />, l.observations || null),
    },
  ]
}

function colonnes4(r: ReceptionFiche): Colonne<LigneReception>[] {
  return [
    {
      cle: 'prix',
      titre: 'Prix / kg',
      aide: 'Le prix payé : celui du bon confirmé, sinon celui saisi (ou du catalogue)',
      droite: true,
      rendu: (l) =>
        deux(
          <span className={styles.sansCoupure}>{prixUnite(l.prix, r.devise, 'kg')}</span>,
          l.prix_confirme ? 'du bon' : null,
        ),
    },
  ]
}

function colonnes(r: ReceptionFiche): Colonne<LigneReception>[] {
  return [...colonnes1(r), ...colonnes2(r), ...colonnes3(r), ...colonnes4(r)]
}

export function VoletLignesReception({ r }: { r: ReceptionFiche }) {
  return (
    <div className={styles.volet}>
      <div className={styles.tableFenetre}>
        <DataTable<LigneReception>
          libelle="Lignes pesées"
          lignes={r.lignes}
          colonnes={colonnes(r)}
          cle={(l) => l.id}
          recherche={false}
          hauteur="fenetre"
        />
      </div>
      {r.observations ? <span className={styles.note}>Observations : {r.observations}</span> : null}
    </div>
  )
}
