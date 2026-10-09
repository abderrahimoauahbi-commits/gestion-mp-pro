/**
 * L'apparence de l'écran, choisie dans « Mon compte » et retenue par ce navigateur : selon le
 * poste (`prefers-color-scheme`), claire ou sombre (`<html data-theme>`, `styles/jetons.css`).
 */
export type Theme = 'poste' | 'clair' | 'sombre'

export const CLE_THEME = 'gestion-mp-pro:theme'

export function lireTheme(): Theme {
  try {
    const v = window.localStorage.getItem(CLE_THEME)
    return v === 'clair' || v === 'sombre' ? v : 'poste'
  } catch {
    return 'poste'
  }
}

/** Pose l'apparence sur la page (et la retient si `retenir`). */
export function appliquerTheme(theme: Theme = lireTheme(), retenir = false): void {
  if (theme === 'poste') document.documentElement.removeAttribute('data-theme')
  else document.documentElement.setAttribute('data-theme', theme)
  if (!retenir) return
  try {
    if (theme === 'poste') window.localStorage.removeItem(CLE_THEME)
    else window.localStorage.setItem(CLE_THEME, theme)
  } catch {
    /* stockage refusé : l'apparence vaut pour cette page seulement */
  }
}

/**
 * Le papier est blanc : l'impression se fait dans l'apparence claire, quelle que soit celle de
 * l'écran, puis l'apparence choisie revient.
 */
export function imprimerEnClair(): () => void {
  const avant = () => document.documentElement.setAttribute('data-theme', 'clair')
  const apres = () => appliquerTheme()
  window.addEventListener('beforeprint', avant)
  window.addEventListener('afterprint', apres)
  return () => {
    window.removeEventListener('beforeprint', avant)
    window.removeEventListener('afterprint', apres)
  }
}
