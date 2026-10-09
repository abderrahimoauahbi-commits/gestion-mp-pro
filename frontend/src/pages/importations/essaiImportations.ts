/**
 * Les données d'essai des importations (essais vitest seulement) : réponses réelles du serveur
 * (`donneesEssai.json`, base d'essai du lot F5 semée par l'API : un dossier ouvert avec deux frais,
 * un dossier clos, deux factures qui attendent leur dossier, les postes de frais), et le faux
 * serveur qui les sert au rôle voulu.
 */
import { fauxServeur, reponsesConnecte, type Reponse } from '../../essais/monter'
import type { Role } from '../../lib/types'
import brut from './donneesEssai.json'
import type { ApercuDossiers, DossierFiche, DossierResume, EnAttente, PosteFiche } from './types'

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

/** Le texte cherché d'un dossier (comme le serveur : champs et dérivés). */
function texte(x: DossierResume): string {
  const morceaux = [x.numero, x.libelle, x.banque, x.commentaire, ...x.factures, ...x.fournisseurs]
  morceaux.push(...x.receptions.map((r) => r.numero), ...x.familles.map((f) => f.famille))
  return morceaux.join(' ').toLowerCase()
}

/** Les dossiers du filtre demandé (statut, recherche, fournisseur, « à vérifier »), comme le serveur. */
function filtres(dossiers: DossierResume[], url: URL): DossierResume[] {
  const statut = url.searchParams.get('statut')
  const q = (url.searchParams.get('q') ?? '').trim().toLowerCase()
  const fournisseur = url.searchParams.get('fournisseur')
  const verifier = url.searchParams.get('verifier')
  let gardes =
    statut === 'annule'
      ? []
      : statut
        ? dossiers.filter((x) => x.statut === statut)
        : dossiers.filter((x) => x.statut !== 'annule')
  if (q) gardes = gardes.filter((x) => q.split(/\s+/).every((m) => texte(x).includes(m)))
  if (fournisseur) gardes = gardes.filter((x) => String(x.facture?.fournisseur_id) === fournisseur)
  if (verifier) gardes = gardes.filter((x) => x.a_verifier.length > 0 === (verifier === 'oui'))
  return gardes
}

/** L'aperçu (route 250) calculé sur un ensemble de dossiers, comme le serveur. */
function apercuDe(dossiers: DossierResume[]): ApercuDossiers {
  const somme = (f: (x: DossierResume) => number) => dossiers.reduce((s, x) => s + f(x), 0)
  const fournisseurs = new Map<number, string>()
  for (const x of dossiers) if (x.facture) fournisseurs.set(x.facture.fournisseur_id, x.facture.fournisseur)
  return {
    ouvert: dossiers.filter((x) => x.statut === 'ouvert').length,
    clos: dossiers.filter((x) => x.statut === 'clos').length,
    annule: dossiers.filter((x) => x.statut === 'annule').length,
    nombre: dossiers.length,
    poids: somme((x) => x.poids),
    marchandise_mad: somme((x) => x.marchandise_mad),
    charges_mad: somme((x) => x.charges_mad),
    revient_mad: somme((x) => x.revient_mad),
    decaisse_mad: somme((x) => x.decaisse_mad),
    non_repartis: dossiers
      .filter((x) => Math.abs(x.charges_non_reparties_mad) > 0.005)
      .map((x) => ({ id: x.id, numero: x.numero, montant: x.charges_non_reparties_mad })),
    fournisseurs: [...fournisseurs].map(([id, nom]) => ({ id, nom })),
  }
}

/** Le faux serveur des importations : liste paginée, aperçu, attente, fiche, postes, pièces. */
export function serveurImportations(role: Role, d: Donnees, autres: Record<string, Reponse> = {}) {
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /dossiers': (_c, url) => {
      const elements = filtres(d.dossiers, url)
      return { corps: { elements, total: elements.length, suivant: null } }
    },
    'GET /dossiers/apercu': (_c, url) => ({ corps: apercuDe(filtres(d.dossiers, url)) }),
    'GET /dossiers/a-rattacher': { corps: d.attente },
    [`GET /dossiers/${d.fiche.id}`]: { corps: d.fiche },
    'GET /postes-frais': { corps: d.postes },
    'GET /pieces': { corps: [] },
    [`GET /historique/dossier/${d.fiche.id}`]: { corps: [] },
    ...autres,
  })
}
