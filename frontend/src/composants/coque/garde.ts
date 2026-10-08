/**
 * Ne jamais perdre une saisie en naviguant (REGLES-ECRAN § 3, H-10, P1-22, P2-10).
 *
 * Une fenêtre (`Fenetre({sale})`) déclare déjà sa saisie non enregistrée dans la pile
 * (`mise-en-page/pile.ts`) ; une saisie posée à même la page (plan de production, paramètres…)
 * la déclare par `useGardeSaisie(sale)`. Tant qu'une saisie est en cours :
 * - « Précédent » / « Suivant » du navigateur sont retenus (routeur de données, `useBlocker`) —
 *   c'était la limite de Gestion MP, dont le routeur ne le permettait pas ;
 * - un clic sur un lien de l'application (menu, fil d'Ariane, n° de document…) est retenu ;
 * - les gestes de la coque qui quittent la page (recherche globale, notification, menu du compte)
 *   passent par `proteger(action)` ;
 * - fermer ou recharger l'onglet du navigateur est retenu par le navigateur (`beforeunload`, pile).
 * La question est « Des modifications ne sont pas enregistrées. Les abandonner ? » ;
 * « Oui, abandonner » laisse partir, « Non, continuer la saisie » reste.
 *
 * Les navigations décidées par la page elle-même (fermer une fiche après « Enregistrer », « Oui,
 * abandonner » d'une fenêtre) ne sont pas retenues : c'est la page qui sait que sa saisie est
 * enregistrée ou abandonnée.
 */
import { useEffect, useState } from 'react'

import { marquerSale, saisieEnCours } from '../mise-en-page/pile'

export { saisieEnCours }

type Demande = (action: () => void) => void

const auditeurs = new Set<Demande>()

/** L'action a lieu tout de suite, ou après « Oui, abandonner » s'il y a une saisie en cours. */
export function proteger(action: () => void): void {
  const poseur = [...auditeurs].pop()
  if (!saisieEnCours() || !poseur) {
    action()
    return
  }
  poseur(action)
}

/** Branche la question (un seul `GardeNavigation`, à la racine de l'application). */
export function ecouterDemandes(demande: Demande): () => void {
  auditeurs.add(demande)
  return () => {
    auditeurs.delete(demande)
  }
}

/** La page porte une saisie non enregistrée tant que `sale` est vrai. */
export function useGardeSaisie(sale: boolean): void {
  const [moi] = useState(() => Symbol('saisie de page'))
  useEffect(() => {
    marquerSale(moi, sale)
    return () => marquerSale(moi, false)
  }, [moi, sale])
}

/** Le lien interne visé par un clic, s'il faut le retenir (`null` sinon). */
export function lienRetenu(e: MouseEvent, ici: string): string | null {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return null
  const cible = e.target instanceof Element ? e.target.closest('a[href]') : null
  if (!(cible instanceof HTMLAnchorElement)) return null
  if (cible.target && cible.target !== '_self') return null
  if (cible.hasAttribute('download')) return null
  const url = new URL(cible.href, window.location.href)
  if (url.origin !== window.location.origin || url.pathname.startsWith('/api/')) return null
  if (url.pathname === ici) return null
  return `${url.pathname}${url.search}${url.hash}`
}
