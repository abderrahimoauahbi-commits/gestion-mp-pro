/**
 * Ce que dit l'écran après un geste sur un bon (textes de Gestion MP, ECRANS-PRO 4.7–4.10), sans
 * écran : le serveur rend la fiche, l'écran compare l'avant et l'après.
 */
import { date, montant, nombre } from '../../lib/format'
import type { CommandeFiche } from './types'

type Etat = Pick<CommandeFiche, 'statut' | 'numero' | 'montant_estime_mad' | 'date_commande'>

/**
 * La part reçue sous réserve qui attend en quarantaine (D-02, décision V1) : le reste à livrer du
 * bon la compte reçue (règle de Gestion MP, gardée pour la parité), le Cockpit et le plan d'achat
 * l'attendent encore jusqu'à sa libération. Une seule phrase, sur la ligne et sur la fiche.
 */
export function texteReserve(kg: number): string {
  return `dont ${nombre(kg)} kg reçus sous réserve, en quarantaine : attendus jusqu’à leur libération`
}

/** Après « Enregistrer » (lignes, date, remarques). */
export function apresModification(avant: Etat, apres: Etat): string {
  if (avant.statut === 'a_approuver' && apres.statut === 'brouillon')
    return 'Bon modifié pendant que la direction le relisait : il revient en brouillon. Soumettez-le de nouveau quand il est prêt.'
  if (avant.statut === 'a_approuver' && apres.numero && apres.statut !== 'a_approuver')
    return 'Bon ramené à ce que la direction avait accepté : il n’a plus besoin d’elle et reprend sa route.'
  if (apres.statut === 'a_approuver')
    return `Bon modifié : il dépasse désormais le seuil d’approbation (≈ ${montant(apres.montant_estime_mad, 'MAD')}) et repasse par la direction. Ne le renvoyez pas au fournisseur avant son accord.`
  return apres.numero
    ? 'Bon modifié. Il est déjà parti : réimprimez-le et renvoyez-le au fournisseur.'
    : 'Bon modifié.'
}

/** Après « Envoyer, ou demander l'approbation ». */
export function apresEnvoi(apres: Etat): string {
  if (apres.statut === 'a_approuver') return 'Bon soumis à la direction : il partira à son approbation.'
  return `Bon envoyé : il porte désormais le n° ${apres.numero ?? ''}, daté du ${date(apres.date_commande)}. Les prix seront à confirmer au retour du fournisseur.`
}

/** Après « Confirmer ces prix ». */
export function apresPrix(saisis: number, auCatalogue: number, reste: number): string {
  return (
    `${nombre(saisis)} prix confirmé(s)` +
    (auCatalogue ? `, ${nombre(auCatalogue)} reporté(s) au catalogue` : '') +
    '.' +
    (reste ? ` Il reste ${nombre(reste)} prix à confirmer.` : '')
  )
}

/** Après « Enregistrer le suivi ». */
export function apresSuivi(etaAvant: string | null, etaApres: string | null): string {
  return etaApres && etaApres !== etaAvant
    ? `Suivi enregistré. L’arrivée prévue (ETA) du ${date(etaApres)} remplace la livraison prévue dans le calcul du stock.`
    : 'Suivi de l’expédition enregistré.'
}
