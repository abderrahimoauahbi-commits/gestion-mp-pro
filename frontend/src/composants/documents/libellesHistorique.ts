/**
 * Comment l'historique d'une fiche dit un champ et sa valeur (`LigneHistorique` de S2, route 51) :
 * le journal range les différences sous le **nom de la colonne** (`prix`, `fournisseur_id`…) et
 * les valeurs telles qu'en base (nombres, dates ISO, listes). On les lit ici à la française,
 * selon `lib/format`.
 */
import { cours, date, horodatage, nombre, prix, VIDE } from '../../lib/format'

/** Les colonnes des fiches qui ont un onglet Historique (matière, fournisseur, qualité, bon…). */
const LIBELLES: Readonly<Record<string, string>> = {
  actif: 'En service',
  banque: 'Banque',
  base_mensuelle: 'Base mensuelle',
  bobines_palette: 'Bobines par palette',
  code: 'Code',
  code_douanier_id: 'Code douanier',
  composition_id: 'Composition',
  conditions_paiement: 'Conditions de paiement',
  contact: 'Contact',
  contenance_achat: 'Contenance d’achat',
  couleur_code: 'Code couleur',
  couleur_id: 'Couleur',
  couv_min_mois: 'Couverture minimale (mois)',
  couverture_commande_jours: 'Couverture de commande (jours)',
  date_commande: 'Date du bon',
  date_livraison_prevue: 'Livraison prévue',
  delai_jours: 'Délai (jours)',
  delai_paiement_jours: 'Délai de paiement (jours)',
  densite: 'Densité',
  designation: 'Désignation',
  devise: 'Devise',
  email: 'Courriel',
  fournisseur_id: 'Fournisseur',
  groupe_equiv: 'Groupe d’équivalence',
  incoterm: 'Incoterm',
  minimum_commande: 'Minimum de commande',
  mode_paiement: 'Mode de paiement',
  nom: 'Nom',
  notes: 'Notes',
  observations: 'Observations',
  pays: 'Pays',
  poids: 'Poids par rôle',
  poids_bobine: 'Poids d’une bobine',
  port_chargement: 'Port de chargement',
  prix: 'Prix',
  priorite_equiv: 'Priorité dans le groupe',
  recette: 'Recette',
  reference: 'Référence',
  role_id: 'Rôle',
  statut: 'Statut',
  stock_min: 'Stock minimum',
  telephone: 'Téléphone',
  titrage_id: 'Titrage',
  type_fil_id: 'Type',
  unite_achat: 'Unité d’achat',
  unite_prix: 'Unité du prix',
}

/** Le libellé d'un champ : connu, sinon le nom de la colonne rendu lisible (`delai_x_id` → « Delai x »). */
export function libelleChamp(champ: string): string {
  const connu = LIBELLES[champ]
  if (connu) return connu
  const mots = champ.replace(/_id$/, '').replace(/_/g, ' ').trim()
  return mots ? mots.charAt(0).toUpperCase() + mots.slice(1) : champ
}

/** Un montant, un coût, un cours : la règle de `lib/format` selon le nom de la colonne. */
function nombreDuChamp(champ: string, v: number): string {
  if (/^(prix|cout|cmup)/.test(champ)) return prix(v)
  if (/^cours/.test(champ)) return cours(v)
  if (/^(montant|valeur|frais|tva|droits|economie|revient)/.test(champ) || champ.endsWith('_mad')) {
    return nombre(v, 2)
  }
  return nombre(v, 0, 4)
}

/** Une valeur d'avant ou d'après, à la française (« — » pour un vide). */
export function valeurLisible(v: unknown, champ = ''): string {
  if (v == null || v === '') return VIDE
  if (typeof v === 'number') return nombreDuChamp(champ, v)
  if (typeof v === 'boolean') return v ? 'oui' : 'non'
  if (typeof v === 'string') {
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return date(v)
    if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/.test(v)) return horodatage(v)
    return v
  }
  if (Array.isArray(v)) return v.length === 1 ? '1 ligne' : `${nombre(v.length)} lignes`
  return JSON.stringify(v)
}

/** Un champ changé, lisible. */
export interface Changement {
  champ: string
  libelle: string
  avant: string
  apres: string
}

type Valeurs = Readonly<Record<string, unknown>> | null | undefined

/**
 * Les noms des identifiants d'une fiche, par champ (`fournisseur_id` → id → « HASIRCI ») : la page
 * qui les a déjà lus les donne, l'historique dit alors « Fournisseur : HASIRCI → LOMAT ».
 */
export type NomsHistorique = Readonly<Record<string, ReadonlyMap<number, string>>>

/** La valeur à lire : le nom de l'identifiant quand la page le connaît. */
const nommee = (champ: string, v: unknown, noms: NomsHistorique | undefined) =>
  (typeof v === 'number' && noms?.[champ]?.get(v)) || v

const vide = (v: unknown) => v == null || v === ''

/**
 * Les champs changés d'une ligne, dans l'ordre du journal. Un champ vide des deux côtés n'est
 * pas montré : c'est un prix que le serveur a retiré pour un rôle qui ne les voit pas.
 */
export function changementsDe(avant: Valeurs, apres: Valeurs, noms?: NomsHistorique): Changement[] {
  const champs = [...Object.keys(apres ?? {}), ...Object.keys(avant ?? {})]
  return [...new Set(champs)]
    .filter((c) => c !== 'id' && !(vide(avant?.[c]) && vide(apres?.[c])))
    .map((c) => ({
      champ: c,
      libelle: libelleChamp(c),
      avant: valeurLisible(nommee(c, avant?.[c], noms), c),
      apres: valeurLisible(nommee(c, apres?.[c], noms), c),
    }))
}
