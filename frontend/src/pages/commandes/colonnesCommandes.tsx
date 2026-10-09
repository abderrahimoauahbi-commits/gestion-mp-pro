/**
 * Les colonnes de la liste des bons (ECRANS-PRO 4.5) : n° ou badge « Brouillon » / « À approuver »
 * (jamais « Brouillon / Brouillon »), montants dans la devise du bon et en MAD (jamais additionnés
 * entre devises), état de livraison en badge de la table unique, bouton de ligne.
 */
import { Badge } from '../../composants/retour/Badge'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { date, montant, nombre, part, VIDE } from '../../lib/format'
import { statut } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { prixAConfirmer } from './liste'
import type { CommandeResume } from './types'

function Numero({ c }: { c: CommandeResume }) {
  const haut = c.numero ? (
    <span className={`${styles.fort} ${styles.sansCoupure}`}>{c.numero}</span>
  ) : (
    <Badge famille="commande" valeur={c.statut} />
  )
  return deux(haut, c.parti ? date(c.date_commande) : 'daté à l’envoi')
}

function Montant({ c }: { c: CommandeResume }) {
  if (c.nb_lignes && c.prix_a_confirmer >= c.nb_lignes)
    return deux(`≈ ${montant(c.montant_estime, c.devise)}`, 'prix à confirmer')
  return deux(
    montant(c.montant_estime, c.devise),
    c.prix_a_confirmer ? `${nombre(c.prix_a_confirmer)} prix à confirmer` : null,
  )
}

function Livraison({ c }: { c: CommandeResume }) {
  const note = !c.parti
    ? 'pas envoyé'
    : c.livree_le
      ? `livrée le ${date(c.livree_le)}`
      : c.derniere_reception_le
        ? `${part(c.part_livree, 0)} livré · dernière arrivée le ${date(c.derniere_reception_le)}`
        : null
  return deux(<Badge famille="livraison" valeur={c.livraison} />, note)
}

function Prevue({ c }: { c: CommandeResume }) {
  if (c.expedition.eta)
    return deux(date(c.expedition.eta), ['ETA', c.expedition.conteneur].filter(Boolean).join(' · '))
  return <>{c.date_livraison_prevue ? date(c.date_livraison_prevue) : VIDE}</>
}

function colonnesCommandes1(
  _ouvrir: (c: CommandeResume, onglet?: string) => void,
): Colonne<CommandeResume>[] {
  return [
    {
      cle: 'numero',
      titre: 'N° · date',
      aide: 'La date du bon est celle de son envoi',
      valeur: (c) => c.numero ?? '',
      rendu: (c) => <Numero c={c} />,
    },
    {
      cle: 'fournisseur',
      titre: 'Fournisseur',
      rendu: (c) => (
        <span title={c.references.join('\n')}>
          {deux(
            <span className={styles.fort}>{c.fournisseur}</span>,
            c.references.length
              ? `${c.references[0]}${c.references.length > 1 ? ` + ${c.references.length - 1}` : ''}`
              : null,
          )}
        </span>
      ),
    },
    {
      cle: 'quantite',
      titre: 'Quantité (kg)',
      aide: 'En kilos, le cuir, les franges et le ruban compris',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (c) => nombre(c.quantite),
    },
    {
      cle: 'montant',
      titre: 'Montant',
      droite: true,
      unite: (c) => c.devise,
      total: true,
      valeur: (c) => c.montant_estime,
      rendu: (c) => <Montant c={c} />,
    },
  ]
}

function colonnesCommandes2(
  _ouvrir: (c: CommandeResume, onglet?: string) => void,
): Colonne<CommandeResume>[] {
  return [
    {
      cle: 'montant_mad',
      titre: 'Montant MAD',
      aide: 'Au cours figé à la confirmation, sinon au cours du jour ; prix du catalogue tant que le prix n’est pas confirmé',
      droite: true,
      unite: 'MAD',
      total: true,
      valeur: (c) => c.montant_estime_mad,
      rendu: (c) => montant(c.montant_estime_mad, 'MAD'),
    },
    {
      cle: 'livraison',
      titre: 'État de livraison',
      aide: 'Où en est la livraison du bon',
      valeur: (c) => statut('livraison', c.livraison).libelle,
      rendu: (c) => <Livraison c={c} />,
    },
    {
      cle: 'prevue',
      titre: 'Prévue / ETA',
      aide: 'La livraison prévue, ou l’arrivée prévue (ETA) du suivi d’expédition',
      valeur: (c) => c.expedition.eta ?? c.date_livraison_prevue ?? '',
      rendu: (c) => <Prevue c={c} />,
    },
    {
      cle: 'statut',
      titre: 'Statut',
      valeur: (c) => statut('commande', c.statut).libelle,
      rendu: (c) =>
        deux(<Badge famille="commande" valeur={c.statut} />, c.renvoi ? 'renvoyé par la direction' : null),
    },
  ]
}

function colonnesCommandes3(ouvrir: (c: CommandeResume, onglet?: string) => void): Colonne<CommandeResume>[] {
  return [
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (c) => (
        <span className={styles.sansCoupure} onClick={(e) => e.stopPropagation()}>
          {prixAConfirmer(c) ? (
            <Bouton
              taille="petit"
              titre="Ouvre le bon sur les prix du fournisseur"
              onClick={() => ouvrir(c, 'prix')}
            >
              Saisir les prix
            </Bouton>
          ) : (
            <Bouton
              taille="petit"
              variante={c.statut === 'a_approuver' ? 'principal' : 'neutre'}
              onClick={() => ouvrir(c)}
            >
              Ouvrir
            </Bouton>
          )}
        </span>
      ),
    },
  ]
}

export function colonnesCommandes(
  ouvrir: (c: CommandeResume, onglet?: string) => void,
): Colonne<CommandeResume>[] {
  return [...colonnesCommandes1(ouvrir), ...colonnesCommandes2(ouvrir), ...colonnesCommandes3(ouvrir)]
}

/** Les champs cherchés sans être affichés (N°, pays, conteneur, remarques, références…). */
export const CHERCHES = (c: CommandeResume) => [
  c.numero ?? 'Brouillon',
  c.pays,
  c.devise,
  c.statut_libelle,
  c.livraison_libelle,
  c.cree_par,
  c.observations,
  c.expedition.conteneur,
  c.expedition.navire,
  ...c.references,
]

export function filtresCommandes(noms: ReadonlyMap<string, string>): Filtre<CommandeResume>[] {
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (c) => String(c.fournisseur_id),
      libelleValeur: (v) => noms.get(v) ?? v,
    },
    { cle: 'devise', libelle: 'Devise', valeur: (c) => c.devise },
    {
      cle: 'livraison',
      libelle: 'État de livraison',
      valeur: (c) => c.livraison,
      libelleValeur: (v) => statut('livraison', v).libelle,
    },
  ]
}
