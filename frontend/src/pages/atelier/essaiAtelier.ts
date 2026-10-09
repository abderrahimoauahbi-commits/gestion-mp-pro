/**
 * Les données d'essai de l'atelier et des métiers (essais vitest seulement) : réponses réelles du
 * serveur, lues au rôle alimentation sur une base d'essai semée par l'API (`donneesEssai.json`,
 * aucun prix), et le faux serveur qui les sert.
 */
import { reponsesConnecte, type Reponse } from '../../essais/monter'
import type { Role } from '../../lib/types'
import brut from './donneesEssai.json'
import type {
  LotFiche,
  LotSolde,
  LotSorti,
  MagasinFiche,
  MatiereMontage,
  MetierFiche,
  Motifs,
  OrdreFiche,
  Proposition,
  QualiteResume,
} from './types'

export interface Donnees {
  MAGASINS: MagasinFiche[]
  MOTIFS: Motifs
  QUALITES: QualiteResume[]
  METIERS: MetierFiche[]
  MATIERES_MONTAGE: MatiereMontage[]
  ORDRE_VALIDE: OrdreFiche
  LOTS_SORTIS: LotSorti[]
  LOTS: LotSolde[]
  LOT: LotFiche
  PROPOSITION: Proposition
}

/** Une copie fraîche des données (chaque essai peut la modifier). */
export function donnees(): Donnees {
  return JSON.parse(JSON.stringify(brut))
}

/** Le faux serveur de l'atelier : les lectures communes, plus `autres`. */
export function reponsesAtelier(role: Role, autres: Record<string, Reponse> = {}): Record<string, Reponse> {
  const d = donnees()
  const brouillon: OrdreFiche = {
    ...d.ORDRE_VALIDE,
    id: 5,
    numero: null,
    statut: 'brouillon',
    valide_par: '',
    valide_le: null,
  }
  return reponsesConnecte(role, {
    'GET /magasins': { corps: d.MAGASINS },
    'GET /motifs': { corps: d.MOTIFS },
    'GET /qualites': { corps: d.QUALITES },
    'GET /metiers': { corps: d.METIERS },
    'GET /metiers/1': { corps: d.METIERS.find((m) => m.id === 1) },
    'GET /montage/matieres': { corps: d.MATIERES_MONTAGE },
    'GET /ordres': (_c, url) => ({
      corps: url.searchParams.get('statut') === 'brouillon' ? [brouillon] : [d.ORDRE_VALIDE, brouillon],
    }),
    'GET /ordres/1': { corps: d.ORDRE_VALIDE },
    'GET /ordres/5': { corps: brouillon },
    'GET /ordres/1/lots-sortis': { corps: d.LOTS_SORTIS },
    'GET /lots': { corps: d.LOTS },
    'GET /lots/1': { corps: d.LOT },
    'GET /matieres': { corps: [] },
    'GET /signalements': { corps: { elements: [], total: 0, suivant: null } },
    'POST /ordres/proposition': { corps: d.PROPOSITION },
    ...autres,
  })
}

/** Ce qui trahirait un prix, un montant ou une devise dans le texte d'un écran (an. 27). */
export const MONETAIRE = /\b(USD|MAD|EUR)\b|[Pp]rix|[Cc]oût|[Mm]ontant|DH\b/
