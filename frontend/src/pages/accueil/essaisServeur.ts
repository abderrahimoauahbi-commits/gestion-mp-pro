/**
 * Le faux serveur des essais de Ma journée et du Cockpit : les réponses relevées au vrai serveur
 * (base d’essai du lot F1, dossiers `essais` de accueil et cockpit), par rôle. Un changement de schéma les rend fausses :
 * les relever de nouveau.
 */
import { fauxServeur, reponsesConnecte, type Reponse } from '../../essais/monter'
import type { Role } from '../../lib/types'
import brouillonsD from '../cockpit/essais/brouillons.json'
import cockpit from '../cockpit/essais/cockpit.json'
import commandes from '../cockpit/essais/commandes.json'
import historique from '../cockpit/essais/historique.json'
import matieres from '../cockpit/essais/matieres.json'
import retards from '../cockpit/essais/retards.json'
import sauvegardes from '../cockpit/essais/sauvegardes.json'
import stock from '../cockpit/essais/stock.json'
import attente from './essais/attente.json'
import brouillonsA from './essais/brouillons-achats.json'
import brouillonsL from './essais/brouillons-alimentation.json'
import inventaires from './essais/inventaires.json'
import reclamations from './essais/reclamations.json'
import signalements from './essais/signalements.json'

export const DONNEES = { cockpit, commandes, retards, signalements, stock, historique }

/** Le faux serveur d'un rôle ; `autres` remplace ou ajoute des routes. */
export function servirJournee(role: Role, autres: Record<string, Reponse> = {}) {
  const brouillons = { direction: brouillonsD, achats: brouillonsA, alimentation: brouillonsL }
  return fauxServeur({
    ...reponsesConnecte(role),
    'GET /cockpit': { corps: cockpit },
    'GET /commandes': (_c, url) => ({
      corps: url.searchParams.get('filtre') === 'retard' ? retards : commandes,
    }),
    'GET /brouillons': { corps: role === 'administrateur' ? brouillonsD : brouillons[role] },
    'GET /dossiers/a-rattacher': { corps: attente },
    'GET /signalements': { corps: signalements },
    'GET /reclamations': { corps: reclamations },
    'GET /inventaires': { corps: inventaires },
    'GET /sauvegardes': { corps: sauvegardes },
    'GET /stock': { corps: stock },
    'GET /matieres': { corps: matieres },
    'GET /indicateurs/historique': { corps: historique },
    ...autres,
  })
}
