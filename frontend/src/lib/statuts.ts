/**
 * La table unique statut → libellé → ton (ECRANS-PRO § 3, `Badge`). Un statut ne se dit qu'ici :
 * plus de « Brouillon / Brouillon », plus de deux fonctions de couleur pour la même chose (P2-8).
 *
 * Les valeurs sont celles du serveur (MODELE-DONNEES § 2, énumérations ; statuts calculés du
 * moteur) ; les libellés, ceux de Gestion MP **sans émoticône** (REGLES-ECRAN § 5). Le ton est
 * la couleur du badge (jetons `--ton-<ton>` de `styles/jetons.css`).
 */

export type Ton = 'ok' | 'attention' | 'urgent' | 'critique' | 'rupture' | 'neutre' | 'accent'

export interface Statut {
  libelle: string
  ton: Ton
}

type Table = Record<string, Statut>

const s = (libelle: string, ton: Ton): Statut => ({ libelle, ton })

/** Familles de statuts, chacune avec toutes ses valeurs. */
export const STATUTS = {
  /** Bon de commande (`commande.statut`). */
  commande: {
    brouillon: s('Brouillon', 'neutre'),
    a_approuver: s('À approuver', 'urgent'),
    envoyee: s('Envoyée', 'accent'),
    confirmee: s('Confirmée', 'ok'),
    soldee: s('Soldée', 'neutre'),
    annulee: s('Annulée', 'neutre'),
  },
  /** État de livraison d'un bon (calculé par le serveur). */
  livraison: {
    pas_envoye: s('Pas envoyé', 'neutre'),
    attendu: s('Attendu', 'accent'),
    en_cours: s('En cours', 'attention'),
    sous_reserve: s('Reçu sous réserve', 'attention'),
    partiel_retard: s('Partiel retard', 'critique'),
    en_retard: s('En retard', 'critique'),
    livre: s('Livré', 'ok'),
    solde: s('Soldé', 'neutre'),
    solde_main: s('Soldé à la main', 'neutre'),
    solde_sans_livraison: s('Soldé sans livraison', 'neutre'),
    annule: s('Annulé', 'neutre'),
  },
  /** Décisions sur un bon (`commande_decision.decision`). */
  decision: {
    demande_approbation: s("Demande d'approbation", 'urgent'),
    approbation: s('Approuvé et envoyé', 'ok'),
    renvoi: s('Renvoyé aux achats', 'critique'),
    version_retablie: s('Version partie rétablie', 'neutre'),
    approbation_plus_necessaire: s('Approbation plus nécessaire', 'neutre'),
    retour_brouillon: s('Revenu en brouillon', 'neutre'),
    rouverture: s('Rouvert', 'accent'),
  },
  /** Prix d'une ligne de bon. */
  prix: {
    confirme: s('confirmé', 'ok'),
    a_confirmer: s('à confirmer', 'attention'),
  },
  /** Réception, opération de stock (`StatutDocument`, féminin). */
  document: {
    brouillon: s('Brouillon', 'attention'),
    validee: s('Validée', 'ok'),
    annulee: s('Annulée', 'rupture'),
  },
  /** Ordre de fabrication (`StatutOrdre`, masculin). */
  ordre: {
    brouillon: s('Brouillon', 'attention'),
    valide: s('Validé', 'ok'),
    annule: s('Annulé', 'neutre'),
  },
  /** Qualité d'une ligne de réception. */
  qualite_reception: {
    conforme: s('Conforme', 'ok'),
    reserve: s('Sous réserve', 'attention'),
    refuse: s('Refusé', 'critique'),
  },
  /** Statut calculé d'un lot. */
  lot: {
    disponible: s('Disponible', 'ok'),
    partiel: s('En partie en quarantaine', 'attention'),
    quarantaine: s('En quarantaine', 'critique'),
    epuise: s('Épuisé', 'neutre'),
  },
  /** Statut de couverture d'une matière (moteur) ; « en alerte » = les quatre premiers. */
  stock: {
    RUPTURE: s('RUPTURE', 'rupture'),
    CRITIQUE: s('CRITIQUE', 'critique'),
    URGENT: s('URGENT', 'urgent'),
    ATTENTION: s('ATTENTION', 'attention'),
    OK: s('OK', 'ok'),
    NON_CONSOMMEE: s('NON CONSOMMÉE', 'neutre'),
  },
  /** Priorité du plan d'achat. */
  tier: {
    TIER_1: s('Tier 1', 'rupture'),
    TIER_2: s('Tier 2', 'critique'),
    TIER_3: s('Tier 3', 'attention'),
  },
  /** Urgence d'un fournisseur au plan d'achat (« Urgent · n rupt. … » se compose à l'écran). */
  urgence_achat: {
    urgent: s('Urgent', 'rupture'),
    a_grouper: s('À grouper', 'attention'),
    standard: s('Standard', 'neutre'),
  },
  /** Classement d'un fournisseur (distinct du statut ATTENTION, ECRANS-PRO § 5 E7). */
  classement: {
    strategique: s('Stratégique', 'ok'),
    standard: s('Standard', 'neutre'),
    a_surveiller: s('À surveiller', 'attention'),
    a_challenger: s('À challenger', 'critique'),
  },
  inventaire: {
    ouvert: s('Ouvert', 'attention'),
    valide: s('Validé', 'ok'),
    abandonne: s('Abandonné', 'neutre'),
  },
  dossier: {
    ouvert: s('Ouvert', 'accent'),
    clos: s('Clos', 'ok'),
    annule: s('Annulé', 'neutre'),
  },
  reclamation: {
    ouverte: s('Ouverte', 'attention'),
    close: s('Close', 'neutre'),
  },
  issue_reclamation: {
    avoir: s('Avoir', 'ok'),
    remplacement: s('Remplacement', 'ok'),
    remise: s('Remise', 'ok'),
    refusee: s('Refusée', 'neutre'),
    abandonnee: s('Abandonnée', 'neutre'),
  },
  /** Besoin signalé par l'atelier. */
  signalement: {
    en_attente: s('en attente', 'attention'),
    urgent: s('urgent, en attente', 'critique'),
    traite: s('traité', 'ok'),
  },
  /** Gravité d'un contrôle de cohérence. */
  controle: {
    conforme: s('Conforme', 'ok'),
    garanti: s('Garanti', 'neutre'),
    bloquant: s('Bloquant', 'critique'),
    avertissement: s('À corriger', 'attention'),
    information: s('Pour information', 'neutre'),
  },
  /** État d'une qualité au plan de production. */
  qualite_plan: {
    au_plan: s('au plan', 'ok'),
    pas_de_plan: s('pas de plan', 'attention'),
    sans_recette: s('sans recette', 'critique'),
    recette_incomplete: s('recette incomplète', 'critique'),
    inactive: s('inactive, hors plan', 'neutre'),
  },
  metier: {
    actif: s('en service', 'ok'),
    arrete: s('arrêté', 'neutre'),
  },
  courriel: {
    en_attente: s('En attente', 'attention'),
    envoye: s('Envoyé', 'ok'),
    abandonne: s('Abandonné', 'critique'),
  },
  /** Ton d'une notification (`TonNotification`). */
  notification: {
    info: s('Information', 'accent'),
    succes: s('Fait', 'ok'),
    alerte: s('À voir', 'attention'),
    danger: s('Urgent', 'critique'),
  },
} as const satisfies Record<string, Table>

export type Famille = keyof typeof STATUTS

/** Le libellé et le ton d'un statut ; une valeur inconnue s'affiche telle quelle, en neutre. */
export function statut(famille: Famille, valeur: string | null | undefined): Statut {
  const table: Table = STATUTS[famille]
  if (valeur == null || valeur === '') return s('—', 'neutre')
  return table[valeur] ?? s(valeur, 'neutre')
}

/** Les statuts de stock « en alerte » (Cockpit, Ma journée). */
export const STOCK_EN_ALERTE: readonly string[] = ['RUPTURE', 'CRITIQUE', 'URGENT', 'ATTENTION']

/**
 * La clé de stock d'un libellé du moteur, même ancien (« 🔴 CRITIQUE », « ⚪ NON CONSOMMÉE ») ;
 * `null` si le texte n'en est pas un.
 */
export function cleStock(texte: string | null | undefined): keyof (typeof STATUTS)['stock'] | null {
  const t = (texte ?? '').toUpperCase()
  if (t.includes('RUPTURE')) return 'RUPTURE'
  if (t.includes('CRITIQUE')) return 'CRITIQUE'
  if (t.includes('URGENT')) return 'URGENT'
  if (t.includes('ATTENTION')) return 'ATTENTION'
  if (t.includes('NON CONSOMM') || t.includes('NON_CONSOMM')) return 'NON_CONSOMMEE'
  if (/\bOK\b/.test(t)) return 'OK'
  return null
}

/**
 * Le numéro d'un document, ou son état tant qu'il n'en a pas (numéro donné à l'envoi ou à la
 * validation, M65) : « Brouillon », ou « À approuver » pour un bon soumis à la direction.
 */
export function numeroOuEtat(numero: string | null | undefined, statutDocument?: string): string {
  if (numero) return numero
  return statutDocument === 'a_approuver' ? 'À approuver' : 'Brouillon'
}
