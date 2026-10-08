/**
 * La pile des fenêtres ouvertes (A4) : Échap ne ferme que celle du dessus ; la page dessous ne
 * défile pas tant qu'une fenêtre est ouverte ; une saisie non enregistrée retient la fermeture
 * de l'onglet du navigateur (`beforeunload`).
 */

interface Entree {
  moi: symbol
  element: Element | null
}

const pile: Entree[] = []
const sales = new Set<symbol>()
let debordementAvant = ''

/** Retient la fermeture ou le rechargement de l'onglet tant qu'une fenêtre porte une saisie. */
function retenir(e: BeforeUnloadEvent): void {
  e.preventDefault()
  // Les navigateurs anciens attendent une valeur de retour pour poser leur question.
  e.returnValue = ''
}

/**
 * Une fenêtre s'ouvre : elle passe au-dessus. Deux fenêtres montées ensemble (une fiche et la
 * fenêtre qu'elle contient) s'installent enfant d'abord : celle qui en contient une autre se
 * glisse dessous, pour que l'ordre de la pile soit celui de l'écran.
 */
export function empiler(moi: symbol, element: Element | null = null): void {
  if (!pile.length) {
    debordementAvant = document.body.style.overflow
    document.body.style.overflow = 'hidden'
  }
  const dessous = element ? pile.findIndex((e) => e.element && element.contains(e.element)) : -1
  if (dessous >= 0) pile.splice(dessous, 0, { moi, element })
  else pile.push({ moi, element })
}

/** Une fenêtre se ferme : elle quitte la pile (où qu'elle soit). */
export function depiler(moi: symbol): void {
  const i = pile.findIndex((e) => e.moi === moi)
  if (i >= 0) pile.splice(i, 1)
  marquerSale(moi, false)
  if (!pile.length) document.body.style.overflow = debordementAvant
}

/** Vrai si cette fenêtre est celle du dessus. */
export function auDessus(moi: symbol): boolean {
  return pile[pile.length - 1]?.moi === moi
}

/** Le nombre de fenêtres ouvertes. */
export function profondeur(): number {
  return pile.length
}

/** Déclare (ou lève) la saisie non enregistrée d'une fenêtre. */
export function marquerSale(moi: symbol, sale: boolean): void {
  const avant = sales.size
  if (sale) sales.add(moi)
  else sales.delete(moi)
  if (!avant && sales.size) window.addEventListener('beforeunload', retenir)
  if (avant && !sales.size) window.removeEventListener('beforeunload', retenir)
}

/** Vrai si une fenêtre ouverte porte une saisie non enregistrée. */
export function saisieEnCours(): boolean {
  return sales.size > 0
}
