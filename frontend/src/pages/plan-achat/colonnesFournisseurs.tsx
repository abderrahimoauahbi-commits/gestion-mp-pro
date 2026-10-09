/**
 * La table des fournisseurs du plan d'achat (ECRANS-PRO 4.2), partagée avec « Nouvelle commande »
 * (4.6) : budget par fournisseur, devises jamais additionnées, urgence en badge sans émoticône,
 * « Préparer la commande » sur la ligne.
 */
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Montant } from '../../composants/retour/Montant'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { jours, montant, nombre, part, VIDE } from '../../lib/format'
import styles from './achats.module.css'
import { cleUrgence, texteUrgence, TON_URGENCE } from './libelles'
import type { GroupeFournisseur } from './types'

/** Une valeur et sa note dessous. */
export function deux(haut: ReactNode, bas?: ReactNode) {
  return (
    <>
      {haut}
      {bas ? <span className={styles.dessous}>{bas}</span> : null}
    </>
  )
}

function Urgence({ g }: { g: GroupeFournisseur }) {
  const cle = cleUrgence(g.urgence)
  if (!cle) return <span className={styles.note}>rien à commander</span>
  const [libelle, ...details] = texteUrgence(g).split(' · ')
  return deux(<Badge ton={TON_URGENCE[cle]}>{libelle}</Badge>, details.join(' · ') || null)
}

function Nom({ g }: { g: GroupeFournisseur }) {
  const nom = g.fournisseur_id ? (
    <Link to={`/fournisseurs/${g.fournisseur_id}`} onClick={(e) => e.stopPropagation()}>
      {g.fournisseur}
    </Link>
  ) : (
    g.fournisseur
  )
  const ruptures = g.ruptures ? `${nombre(g.ruptures)} référence(s) en rupture` : ''
  return deux(<span className={styles.fort}>{nom}</span>, [g.contact, ruptures].filter(Boolean).join(' · '))
}

/** Les colonnes ; `preparer` ajoute le bouton « Préparer la commande » de la ligne. */
function colonnesFournisseurs1(_preparer: (g: GroupeFournisseur) => void): Colonne<GroupeFournisseur>[] {
  return [
    { cle: 'fournisseur', titre: 'Fournisseur', rendu: (g) => <Nom g={g} />, recherche: (g) => [g.contact] },
    { cle: 'pays', titre: 'Pays', valeur: (g) => g.pays || VIDE },
    {
      cle: 'devises',
      titre: 'Devise(s)',
      aide: 'Un bon de commande par devise',
      valeur: (g) => (g.devises.length ? g.devises : [g.devise_par_defaut]).join(' '),
      rendu: (g) =>
        deux(
          (g.devises.length ? g.devises : [g.devise_par_defaut]).join(', '),
          g.devises.length > 1 ? 'un bon par devise' : null,
        ),
    },
    {
      cle: 'delai_jours',
      titre: 'Délai',
      aide: 'Délai de livraison déclaré du fournisseur',
      droite: true,
      rendu: (g) => jours(g.delai_jours),
    },
    {
      cle: 'nb_references',
      titre: 'Références',
      aide: 'Matières que le calcul propose de commander chez lui',
      droite: true,
      total: true,
      rendu: (g) => (g.nb_references ? nombre(g.nb_references) : VIDE),
    },
    {
      cle: 'quantite',
      titre: 'Quantité (kg)',
      aide: 'En kilos, le cuir, les franges et le ruban compris',
      droite: true,
      unite: 'kg',
      total: true,
      rendu: (g) => nombre(g.quantite),
    },
  ]
}

function colonnesFournisseurs2(_preparer: (g: GroupeFournisseur) => void): Colonne<GroupeFournisseur>[] {
  return [
    {
      cle: 'montants',
      titre: 'Montant en devise',
      aide: 'Au prix du catalogue, avant confirmation par le fournisseur',
      droite: true,
      valeur: (g) => g.montant_mad,
      rendu: (g) => <Montant parDevise={g.montants_par_devise} />,
      exporte: false,
    },
    {
      cle: 'montant_mad',
      titre: 'Contre-valeur MAD',
      aide: 'Au cours du jour de chaque devise ; dessous, la part de ce fournisseur dans le budget du plan d’achat',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (g) =>
        deux(montant(g.montant_mad, 'MAD'), g.part_budget ? `${part(g.part_budget, 0)} du budget` : null),
    },
    { cle: 'urgence', titre: 'Urgence', valeur: (g) => texteUrgence(g), rendu: (g) => <Urgence g={g} /> },
  ]
}

function colonnesFournisseurs3(preparer: (g: GroupeFournisseur) => void): Colonne<GroupeFournisseur>[] {
  return [
    {
      cle: 'preparer',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (g) =>
        g.fournisseur_id ? (
          <span onClick={(e) => e.stopPropagation()}>
            <Bouton
              taille="petit"
              variante={g.nb_references ? 'principal' : 'neutre'}
              titre="Préparer la commande : la proposition s’ouvre, vous cochez, ajustez, et le bon est créé en brouillon"
              onClick={() => preparer(g)}
            >
              Préparer
            </Bouton>
          </span>
        ) : null,
    },
  ]
}

export function colonnesFournisseurs(preparer: (g: GroupeFournisseur) => void): Colonne<GroupeFournisseur>[] {
  return [
    ...colonnesFournisseurs1(preparer),
    ...colonnesFournisseurs2(preparer),
    ...colonnesFournisseurs3(preparer),
  ]
}

export const FILTRES_FOURNISSEURS: Filtre<GroupeFournisseur>[] = [
  { cle: 'urgence', libelle: 'Urgence', valeur: (g) => texteUrgence(g).split(' · ')[0] },
  {
    cle: 'devise',
    libelle: 'Devise',
    valeur: (g) => (g.devises.length ? g.devises : [g.devise_par_defaut]).join(', '),
  },
  { cle: 'pays', libelle: 'Pays', valeur: (g) => g.pays || VIDE },
]
