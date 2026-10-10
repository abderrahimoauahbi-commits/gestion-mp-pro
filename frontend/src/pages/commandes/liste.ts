/**
 * La liste des bons, sans écran : l'onglet d'un bon, le retard, le reste « en prix à confirmer »
 * (ECRANS-PRO 4.5). Les indicateurs et les comptes par onglet sont comptés par le serveur
 * (`/commandes/apercu`) ; ces fonctions servent encore Ma journée et le Cockpit, qui lisent les
 * bons ouverts (`/commandes/ouverts`) et les classent avec `ongletDe`, `enRetard`, `prixAConfirmer`.
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
