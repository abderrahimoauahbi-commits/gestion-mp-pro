/**
 * PROVISOIRE — formes des routes 1–22 et 49–56 (lot S2), écrites à la main d'après API-PRO § 1.1,
 * 1.2, 1.5, 1.6 tant que `types.gen.ts` ne les publie pas. Dès que l'OpenAPI du serveur les
 * contient (`make types`), chaque type ci-dessous se remplace par `Schema<'Nom'>` (`lib/types.ts`)
 * et ce fichier disparaît. Les champs marqués « à aligner » ne sont pas (encore) écrits dans
 * API-PRO : docs/lots/E2.md les liste pour S2.
 */
import type { Role } from './types'

/** GET /etat (route 2, public). */
export interface EtatInstallation {
  installe: boolean
  societe: string
  version?: string
}

/** GET /visages (route 8) : vide hors du poste local et des appareils enrôlés. */
export interface Visage {
  id: number
  nom: string
  role: Role
  /** Longueur du code : l'alimentation entre au 4e chiffre quand elle vaut 4 (H-01). */
  longueur_code?: number | null
  /** À aligner : l'identifiant de connexion, si le serveur le donne avec le visage. */
  identifiant?: string
}

/**
 * POST /connexion (route 10) : `{identifiant, code}` (API-PRO). Depuis un visage, sans
 * identifiant publié, l'écran envoie `{compte, code}` (à aligner avec S2).
 */
export type Connexion = { identifiant: string; code: string } | { compte: number; code: string }

/** POST /installation (route 9). */
export interface Installation {
  societe: string
  identifiant: string
  nom: string
  code: string
}

/** GET /moi (route 12) ; renvoyé aussi par /connexion, /installation et PUT /moi. */
export interface Moi {
  id: number
  identifiant: string
  nom: string
  role: Role
  role_libelle: string
  email: string
  voit_prix: boolean
  droits?: string[]
  /** À aligner : la version de la fiche, exigée par PUT /moi. */
  version?: number
}

/** Compteurs des pastilles du menu (à aligner : ECRANS-PRO § 2.1, « compteurs du menu »). */
export interface CompteursMenu {
  /** Ruptures + critiques (« alerte rouge ») : pastille Stock (D, A, L). */
  alerte_rouge?: number
  /** Contrôles à corriger : pastille Analyse (D, A). */
  anomalies?: number
  /** Bons à approuver : pastille Commandes (D). */
  a_approuver?: number
  /** Réceptions en brouillon : pastille Réceptions (D, A). */
  receptions_brouillon?: number
}

/** L'état du serveur dit à la direction et à l'administrateur (`BandeauServeur`). À aligner. */
export interface AlerteServeur {
  sauvegarde_en_defaut?: boolean
  /** Âge de la dernière sauvegarde, en heures. */
  sauvegarde_age_h?: number | null
  schema_en_retard?: boolean
  base_essai?: boolean
  https_absent?: boolean
}

export interface InventaireOuvert {
  numero: string
  magasin: string
  matieres?: number | null
}

/** GET /contexte (route 3) : tout ce qu'il faut au démarrage, en un appel. */
export interface Contexte {
  moi: Moi
  /** Les entrées de menu permises selon le serveur (chemins) ; l'écran les recoupe avec `routes.ts`. */
  menu?: string[]
  heure_serveur?: string
  date_cloture: string | null
  inventaires_ouverts: InventaireOuvert[]
  societe: string
  alerte_serveur?: AlerteServeur | null
  compteurs?: CompteursMenu
  /** À aligner : vrai sur une base d'essai (bandeau pour tous). */
  base_essai?: boolean
}

export type TonNotification = 'info' | 'succes' | 'alerte' | 'danger'

/** Un élément de GET /notifications (route 53). */
export interface Notification {
  id: number
  texte: string
  lien: string | null
  ton: TonNotification
  quand: string
  lue: boolean
}

/** GET /notifications : `Page[Notification]` + `non_lues`. */
export interface PageNotifications {
  elements: Notification[]
  total: number
  suivant: string | null
  non_lues: number
}

/** Un résultat de GET /recherche?q= (route 56). */
export interface ResultatRecherche {
  genre: string
  id: number
  titre: string
  sous_titre?: string | null
  lien: string
}

/** Un élément de GET /appareils (route 19). */
export interface AppareilFiche {
  id: number
  nom: string
  enrole_le: string | null
  vu_le?: string | null
  revoque_le?: string | null
}

/** GET /matieres (route 70), ce qu'en lit la fenêtre « Signaler un besoin ». */
export interface MatiereResumee {
  id: number
  reference: string
  designation?: string | null
  composition?: string | null
  type_fil?: string | null
  titrage?: string | null
  couleur?: string | null
  fournisseur?: string | null
  actif?: boolean
}
