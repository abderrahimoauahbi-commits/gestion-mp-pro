/**
 * Les colonnes et les filtres de l'onglet « Par matière », sous ses trois vues : l'approvisionnement,
 * le classement et le risque, l'endroit où se trouve la matière. L'alimentation n'a ni montant, ni
 * conseil d'achat (« À commander », « Préparer la commande »), ni classe ABC (H-03).
 *
 * Stock = magasins (quarantaine comprise) + sur les métiers ; Disponible = Stock − quarantaine ;
 * Projeté = Disponible + Commandé (dans le délai) − Demande pendant le délai (une définition
 * serveur, P2-6).
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import type { Colonne } from '../../composants/tableaux/colonnes'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { SUR_LES_METIERS } from '../../lib/aide'
import { date, jours, nombre, part, VIDE } from '../../lib/format'
import { cleStock, STATUTS } from '../../lib/statuts'
import { Double, Kg } from './cellules'
import styles from './stock.module.css'
import { estQuarantaine, POUSSIERE, type LigneStock } from './types'

export type VueMatieres = 'appro' | 'classement' | 'ou'

/** Une ligne du stock, avec ce que le catalogue en dit (rôle, fournisseur par son identifiant). */
export interface LigneMatiere extends LigneStock {
  role: string
  fournisseur_id: number | null
}

const RANGS = Object.keys(STATUTS.stock)

/** Le rang d'un statut, du plus urgent (RUPTURE) au plus calme (NON CONSOMMÉE). */
export function rangStatut(texte: string | null | undefined): number {
  const cle = cleStock(texte)
  return cle ? RANGS.indexOf(cle) : RANGS.length
}

const n = (v: number | null | undefined) => v ?? 0
/** Stock = magasins (quarantaine comprise) + sur les métiers. */
export const stockDetenu = (l: LigneStock) => n(l.stock_net) + n(l.stock_machine)
export const aCommander = (l: LigneStock) => n(l.quantite_a_commander) > POUSSIERE

const kgCol = (
  cle: string,
  titre: string,
  valeur: (l: LigneMatiere) => number | null | undefined,
  aide: string,
  metres = false,
): Colonne<LigneMatiere> => ({
  cle,
  titre,
  aide,
  droite: true,
  unite: 'kg',
  total: true,
  valeur: (l) => valeur(l) ?? null,
  rendu: (l) => <Kg v={valeur(l)} kgParMl={metres ? l.kg_par_ml : null} />,
})

export const AIDE_DISPONIBLE = 'Le stock hors quarantaine : magasins et sur les métiers'

const colonnesFixes: Colonne<LigneMatiere>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    valeur: (l) => l.reference,
    recherche: (l) => [
      l.designation,
      l.nature,
      l.couleur,
      l.composition,
      l.type_fil,
      l.titrage,
      l.groupe_equiv,
    ],
    rendu: (l) => (
      <span className={styles.ref}>
        <Double
          haut={l.reference}
          bas={[l.role, l.designation !== l.reference ? l.designation : ''].filter(Boolean).join(' · ')}
        />
      </span>
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur', valeur: (l) => l.fournisseur ?? '' },
  {
    cle: 'statut',
    titre: 'Statut',
    aide: 'Du plus urgent au plus calme : le stock projeté face au seuil d’alerte',
    valeur: (l) => rangStatut(l.statut),
    recherche: (l) => [l.statut],
    rendu: (l) => <Badge famille="stock" valeur={cleStock(l.statut)} />,
  },
]

const APPRO: Colonne<LigneMatiere>[] = [
  {
    cle: 'couverture_statut',
    titre: 'Statut de couverture',
    aide: 'La couverture en jours face aux réglages « couverture critique » et « couverture d’attention »',
    valeur: (l) => rangStatut(l.statut_couverture),
    rendu: (l) => <Badge famille="stock" valeur={cleStock(l.statut_couverture)} />,
  },
  kgCol('stock', 'Stock (kg)', stockDetenu, 'Magasins (quarantaine comprise) et sur les métiers', true),
  kgCol('metiers', 'Sur les métiers', (l) => l.stock_machine, SUR_LES_METIERS),
  kgCol('disponible', 'Disponible', (l) => l.stock_disponible, AIDE_DISPONIBLE, true),
  kgCol('commande', 'Commandé', (l) => l.bc_en_cours, 'Attendu dans le délai du fournisseur'),
  kgCol(
    'demande',
    'Demande pendant le délai',
    (l) => l.demande_delai,
    'Ce que le plan consommera d’ici la livraison d’une commande passée aujourd’hui : Disponible + Commandé − cette demande = Projeté',
  ),
  kgCol(
    'projete',
    'Projeté',
    (l) => l.stock_projete,
    'Ce qu’il restera à la livraison d’une commande passée aujourd’hui',
  ),
  kgCol('conso', 'Conso / mois', (l) => l.conso_mensuelle, 'Consommation d’un mois de la saison'),
  {
    cle: 'couverture',
    titre: 'Couverture',
    droite: true,
    valeur: (l) => l.couverture_jours ?? null,
    rendu: (l) =>
      l.couverture_jours == null ? <span className={styles.nul}>{VIDE}</span> : jours(l.couverture_jours),
  },
]

const ACHATS: Colonne<LigneMatiere>[] = [
  kgCol(
    'a_commander',
    'À commander',
    (l) => l.quantite_a_commander,
    'En kg ; les unités de commande sont dans la fiche',
    true,
  ),
  {
    cle: 'montant',
    titre: 'Montant MAD',
    droite: true,
    unite: 'MAD',
    total: true,
    valeur: (l) => l.montant_a_commander_mad ?? null,
    rendu: (l) =>
      aCommander(l) ? nombre(l.montant_a_commander_mad) : <span className={styles.nul}>{VIDE}</span>,
  },
]

function colonneAction(preparer: (l: LigneMatiere) => string | null): Colonne<LigneMatiere> {
  return {
    cle: 'action',
    titre: 'Action',
    triable: false,
    exporte: false,
    rendu: (l) => {
      const vers = preparer(l)
      return vers ? (
        <Link
          to={vers}
          onClick={(e) => e.stopPropagation()}
          title="Ce que le calcul propose de commander chez ce fournisseur"
        >
          Préparer la commande
        </Link>
      ) : (
        <span className={styles.nul}>{VIDE}</span>
      )
    },
  }
}

function colonnesAppro(voitPrix: boolean, preparer: (l: LigneMatiere) => string | null) {
  return voitPrix ? [...APPRO, ...ACHATS, colonneAction(preparer)] : APPRO
}

const ABC: Colonne<LigneMatiere>[] = [
  {
    cle: 'abc',
    titre: 'ABC',
    aide: 'Part de la valeur consommée : A = l’essentiel ; trié par rang',
    valeur: (l) => l.rang ?? null,
    rendu: (l) => (
      <Double
        haut={l.classe_abc || VIDE}
        bas={l.rang ? `rang ${l.rang} · ${part(l.pourcentage_cumule, 0)}` : ''}
      />
    ),
  },
  {
    cle: 'valeur',
    titre: 'Conso / an MAD',
    droite: true,
    unite: 'MAD',
    total: true,
    valeur: (l) => l.valeur_conso_annuelle_mad ?? null,
    rendu: (l) => nombre(l.valeur_conso_annuelle_mad),
  },
]

const CLASSEMENT: Colonne<LigneMatiere>[] = [
  {
    cle: 'xyz',
    titre: 'XYZ',
    aide: 'Régularité de la demande : X régulière, Z erratique (CV : coefficient de variation)',
    valeur: (l) => l.classe_xyz ?? '',
    rendu: (l) => <Double haut={l.classe_xyz || VIDE} bas={`CV ${nombre(l.cv_demande, 2)}`} />,
  },
  { cle: 'sourcing', titre: 'Sourcing', valeur: (l) => l.sourcing ?? '' },
  {
    cle: 'groupe',
    titre: 'Équivalences',
    aide: 'Groupe d’équivalence et substituts disponibles',
    valeur: (l) => l.groupe_equiv ?? '',
    rendu: (l) =>
      l.groupe_equiv ? (
        <span title={(l.substituts ?? []).join(' · ')}>
          {l.groupe_equiv}
          {l.substituts?.length ? (
            <span className={styles.dessous}>{l.substituts.length} substitut(s)</span>
          ) : null}
        </span>
      ) : (
        <span className={styles.nul}>{VIDE}</span>
      ),
  },
  {
    cle: 'derniere',
    titre: 'Dernière sortie',
    aide: 'Et depuis combien de jours sans sortie ni entrée ; « dormant » au-delà du seuil des réglages',
    valeur: (l) => l.jours_sans_mouvement ?? null,
    rendu: (l) => (
      <span className={styles.nowrap}>
        {date(l.date_derniere_sortie)}
        {l.jours_sans_mouvement != null ? (
          <span className={styles.note}> · {jours(l.jours_sans_mouvement)}</span>
        ) : null}
        {l.dormant ? (
          <>
            {' '}
            <Badge ton="neutre">dormant</Badge>
          </>
        ) : null}
      </span>
    ),
  },
]

function colonnesClassement(voitPrix: boolean): Colonne<LigneMatiere>[] {
  return voitPrix ? [...ABC, ...CLASSEMENT] : CLASSEMENT
}

function colonnesOu(magasins: readonly { code: string; type: string }[], lignes: readonly LigneMatiere[]) {
  const vides = (code: string) => !lignes.some((l) => Math.abs(l.par_magasin?.[code] ?? 0) > POUSSIERE)
  return [
    kgCol('stock', 'Stock (kg)', stockDetenu, 'Magasins (quarantaine comprise) et sur les métiers', true),
    ...magasins
      .filter((g) => !estQuarantaine(g.type) && !vides(g.code))
      .map((g) => kgCol(`mag:${g.code}`, g.code, (l) => l.par_magasin?.[g.code] ?? 0, `Magasin ${g.code}`)),
    {
      ...kgCol('quarantaine', 'Quarantaine', (l) => l.stock_quarantaine, 'Détenue mais pas disponible'),
      rendu: (l: LigneMatiere) =>
        n(l.stock_quarantaine) > POUSSIERE ? (
          <Badge ton="critique">{nombre(l.stock_quarantaine, 1)}</Badge>
        ) : (
          <Kg v={0} />
        ),
    },
    kgCol('metiers', 'Sur les métiers', (l) => l.stock_machine, SUR_LES_METIERS),
    kgCol('disponible', 'Disponible', (l) => l.stock_disponible, AIDE_DISPONIBLE, true),
    kgCol('commande', 'Commandé', (l) => l.bc_en_cours, 'Attendu dans le délai du fournisseur'),
    kgCol(
      'au_dela',
      'Commandé au-delà',
      (l) => l.bc_hors_horizon,
      'Attendu après le délai : ne compte pas dans le projeté',
    ),
    kgCol('projete', 'Projeté', (l) => l.stock_projete, 'Disponible + Commandé − Demande pendant le délai'),
  ]
}

export function colonnesMatieres(
  vue: VueMatieres,
  voitPrix: boolean,
  magasins: readonly { code: string; type: string }[],
  lignes: readonly LigneMatiere[],
  preparer: (l: LigneMatiere) => string | null,
): Colonne<LigneMatiere>[] {
  if (vue === 'classement') return [...colonnesFixes, ...colonnesClassement(voitPrix)]
  if (vue === 'ou') return [...colonnesFixes, ...colonnesOu(magasins, lignes)]
  return [...colonnesFixes, ...colonnesAppro(voitPrix, preparer)]
}

const titrage = (l: LigneStock) =>
  l.titrage ? `${l.titrage}${l.titrage_unite ? ` ${l.titrage_unite}` : ''}` : ''

/** Les filtres liés de l'onglet (A1) ; la classe ABC n'est pas pour l'alimentation (H-03). */
export function filtresMatieres(voitPrix: boolean): Filtre<LigneMatiere>[] {
  const f: (Filtre<LigneMatiere> | null)[] = [
    {
      cle: 'statut',
      libelle: 'Statut',
      valeur: (l) => cleStock(l.statut),
      libelleValeur: (v) => Object.entries(STATUTS.stock).find(([k]) => k === v)?.[1].libelle ?? v,
    },
    { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (l) => l.fournisseur },
    { cle: 'role', libelle: 'Rôle', valeur: (l) => l.role },
    { cle: 'composition', libelle: 'Composition', valeur: (l) => l.composition },
    { cle: 'type_fil', libelle: 'Type de fil', valeur: (l) => l.type_fil },
    { cle: 'titrage', libelle: 'Titrage', valeur: titrage },
    voitPrix ? { cle: 'abc', libelle: 'Classe ABC', valeur: (l) => l.classe_abc } : null,
    { cle: 'xyz', libelle: 'Classe XYZ', valeur: (l) => l.classe_xyz },
  ]
  return f.filter((x): x is Filtre<LigneMatiere> => x != null)
}
