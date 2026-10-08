/**
 * La recherche qui affine à la frappe (REGLES-ECRAN § 3, M24, M71) : plusieurs mots, dans
 * n'importe quel ordre, sans se soucier des accents ni des majuscules. « rouge 2900 hasi » trouve
 * « PP FRZ-2900 Dtex-Red… » de HASIRCI si chaque mot est quelque part dans la ligne ; « frise
 * rouge » trouve « IMP FRISÉ ROUGE ».
 *
 * Les mots sont cherchés **littéralement** : « % » et « _ » ne sont pas des jokers (ils le
 * seraient dans un `LIKE` SQL ; le serveur les échappe, la même règle s'applique ici).
 *
 * Même normalisation au serveur (`services/recherche.normaliser`, colonne `texte_recherche`) :
 * décomposition NFD, marques diacritiques (U+0300–U+036F) retirées, minuscules, blancs (dont
 * l'espace insécable) réduits à une espace.
 */

/** « IMP FRISÉ  Rouge » → « imp frise rouge ». */
export function sansAccents(texte: string): string {
  return texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/\s+/g, ' ').trim()
}

/** Les mots d'une recherche, normalisés (une recherche vide n'en a aucun). */
export function motsDe(recherche: string): string[] {
  return sansAccents(recherche).split(' ').filter(Boolean)
}

/** Vrai si chaque mot de la recherche est quelque part dans le texte (comparaison littérale). */
export function correspond(texte: string, recherche: string): boolean {
  const mots = motsDe(recherche)
  if (!mots.length) return true
  const cible = sansAccents(texte)
  return mots.every((mot) => cible.includes(mot))
}

/** Le texte cherchable d'une ligne : ses champs (visibles ou cachés) réunis, les vides sautés. */
export function texteDe(champs: unknown[]): string {
  return champs.filter((v) => v != null && v !== '').join(' ')
}

/** Filtre une liste sur le texte réuni de quelques champs. Une recherche vide rend la liste entière. */
export function filtrer<T>(liste: readonly T[], recherche: string, champs: (x: T) => unknown[]): T[] {
  if (!motsDe(recherche).length) return [...liste]
  return liste.filter((x) => correspond(texteDe(champs(x)), recherche))
}

/** Le paramètre `?q=` envoyé au serveur : la recherche nettoyée, ou rien (`undefined`). */
export function parametreRecherche(recherche: string): string | undefined {
  const propre = recherche.replace(/\s+/g, ' ').trim()
  return propre || undefined
}
