/** Une liste de classes CSS, les vides sautées : `classes(styles.bouton, actif && styles.actif)`. */
export function classes(...noms: (string | false | null | undefined)[]): string {
  return noms.filter(Boolean).join(' ')
}
