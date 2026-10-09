/**
 * « Palettes par conteneur » : une aide de calcul, jamais envoyée ni imprimée, retenue par poste et
 * par fournisseur (ECRANS-PRO 4.4, anom. 4.19 : Gestion MP la perdait à la fermeture). Le stockage
 * du navigateur peut manquer (navigation privée) : la préparation marche sans.
 */
const cle = (fournisseurId: number) => `gestion-mp-pro.palettes-conteneur.${fournisseurId}`

export function lirePalettesConteneur(fournisseurId: number): number | null {
  try {
    const v = Number(localStorage.getItem(cle(fournisseurId)))
    return Number.isFinite(v) && v > 0 ? v : null
  } catch {
    return null
  }
}

export function ecrirePalettesConteneur(fournisseurId: number, valeur: number | null): void {
  try {
    if (valeur && valeur > 0) localStorage.setItem(cle(fournisseurId), String(valeur))
    else localStorage.removeItem(cle(fournisseurId))
  } catch {
    /* navigateur sans stockage : l'aide reste pour cette préparation */
  }
}
