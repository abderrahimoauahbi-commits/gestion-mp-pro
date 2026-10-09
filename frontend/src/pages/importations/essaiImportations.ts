/**
 * Les données d'essai des importations (essais vitest seulement) : réponses réelles du serveur
 * (`donneesEssai.json`, base d'essai du lot F5 semée par l'API : un dossier ouvert avec deux frais,
 * un dossier clos, deux factures qui attendent leur dossier, les postes de frais), et le faux
 * serveur qui les sert au rôle voulu.
 */
import { fauxServeur, reponsesConnecte, type Reponse } from '../../essais/monter'
import type { Role } from '../../lib/types'
import brut from './donneesEssai.json'
import type { DossierFiche, DossierResume, EnAttente, PosteFiche } from './types'

export interface Donnees {
  dossiers: DossierResume[]
  attente: EnAttente
  fiche: DossierFiche
  postes: PosteFiche[]
}

/** Une copie fraîche des données (chaque essai peut la modifier). */
export function donnees(): Donnees {
  return JSON.parse(JSON.stringify(brut))
}

/** Le faux serveur des importations : liste, attente, fiche, postes, pièces et historique vides. */
export function serveurImportations(role: Role, d: Donnees, autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /dossiers': (_c, url) => ({
      corps: url.searchParams.get('statut') === 'annule' ? [] : d.dossiers,
    }),
    'GET /dossiers/a-rattacher': { corps: d.attente },
    [`GET /dossiers/${d.fiche.id}`]: { corps: d.fiche },
    'GET /postes-frais': { corps: d.postes },
    'GET /pieces': { corps: [] },
    [`GET /historique/dossier/${d.fiche.id}`]: { corps: [] },
    ...autres,
  })
}
