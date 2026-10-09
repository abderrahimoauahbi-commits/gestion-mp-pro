/**
 * La liste des bons, sans écran : l'onglet d'un bon, le retard, le reste « en prix à confirmer »,
 * et les indicateurs comptés sur **tous** les bons (ECRANS-PRO 4.5).
 */
import type { CommandeResume } from './types'

export const ONGLETS_COMMANDES = ['brouillon', 'a_approuver', 'envoyee', 'confirmee', 'clos'] as const
export type OngletCommandes = (typeof ONGLETS_COMMANDES)[number]

export const LIBELLES_ONGLETS: Record<OngletCommandes, { libelle: string; aide: string }> = {
  brouillon: { libelle: 'Brouillons', aide: 'Pas encore partis, sans numéro : relire, imprimer, envoyer' },
  a_approuver: { libelle: 'À approuver', aide: 'Au-delà du seuil : la direction approuve ou renvoie' },
  envoyee: { libelle: 'Envoyées', aide: 'Partis, prix pas encore tous confirmés' },
  confirmee: { libelle: 'Confirmées', aide: 'Prix confirmés : suivre l’expédition et l’arrivée' },
  clos: { libelle: 'Soldées / annulées', aide: 'Reçus, soldés ou annulés : « Rouvrir » remet en attente' },
}

const CLOS = new Set(['soldee', 'annulee'])

export const estClos = (c: Pick<CommandeResume, 'statut'>) => CLOS.has(c.statut)

/** L'onglet d'un bon. */
export function ongletDe(c: Pick<CommandeResume, 'statut'>): OngletCommandes {
  if (estClos(c)) return 'clos'
  return c.statut === 'a_approuver' || c.statut === 'envoyee' || c.statut === 'confirmee'
    ? c.statut
    : 'brouillon'
}

/** La livraison prévue (ou l'ETA) est dépassée. */
export const enRetard = (c: Pick<CommandeResume, 'livraison'>) =>
  c.livraison === 'en_retard' || c.livraison === 'partiel_retard'

/** Un bon parti, pas clos, avec au moins un prix à confirmer. */
export const prixAConfirmer = (c: CommandeResume) => c.parti && !estClos(c) && c.prix_a_confirmer > 0

export interface IndicateursCommandes {
  ouverts: number
  brouillons: number
  aApprouver: number
  engage: number
  partis: number
  partisEstimes: number
  reste: number
  aConfirmer: number
  retard: number
}

export function indicateurs(bons: readonly CommandeResume[]): IndicateursCommandes {
  const ouverts = bons.filter((c) => !estClos(c))
  const partis = ouverts.filter((c) => c.statut === 'envoyee' || c.statut === 'confirmee')
  return {
    ouverts: ouverts.length,
    brouillons: ouverts.filter((c) => c.statut === 'brouillon').length,
    aApprouver: ouverts.filter((c) => c.statut === 'a_approuver').length,
    engage: partis.reduce((s, c) => s + c.montant_estime_mad, 0),
    partis: partis.length,
    partisEstimes: partis.filter((c) => c.prix_a_confirmer > 0).length,
    reste: ouverts.filter((c) => c.parti).reduce((s, c) => s + c.reste_estime_mad, 0),
    aConfirmer: bons.filter(prixAConfirmer).length,
    retard: ouverts.filter(enRetard).length,
  }
}

/** Le premier onglet qui a des bons (défaut de la liste), sinon les brouillons. */
export function premierOnglet(bons: readonly CommandeResume[]): OngletCommandes {
  return ONGLETS_COMMANDES.find((o) => bons.some((c) => ongletDe(c) === o)) ?? 'brouillon'
}
