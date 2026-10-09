/**
 * La saisie d'une fiche qualité, sans écran : code, nom, état, poids au m² par rôle (ml/m² pour
 * un rôle au mètre) et lignes de la recette ; le corps envoyé — **une seule requête** `PUT
 * /qualites/{id}` pour la fiche et la recette (P7-8) ; la recette n'y part que si elle change.
 */
import type { Matiere } from '../catalogue/types'
import type { LigneSaisie } from './recette'
import type { LigneRecette, QualiteCorps, QualiteFiche } from './types'

export interface FormeQualite {
  code: string
  nom: string
  actif: boolean
  /** Le poids au m² de chaque rôle, par identifiant (absent ou nul : le rôle n'entre pas). */
  poids: Readonly<Record<number, number | null>>
  lignes: readonly LigneSaisie[]
}

/** Une ligne de la recette lue (une matière disparue du catalogue n'a plus d'identifiant). */
export function depuisFiche(l: LigneRecette): LigneSaisie {
  return {
    matiere_id: l.matiere_id ?? 0,
    reference: l.reference,
    nature: l.nature,
    designation: l.designation,
    fournisseur: l.fournisseur,
    role_id: l.role_id,
    pourcentage: l.pourcentage,
    densite: l.densite,
    prix_kg: l.prix_kg,
    prix: l.prix,
    unite_prix: l.unite_prix,
    devise: l.devise_prix,
    disparue: l.matiere_id == null,
  }
}

/** Une matière ajoutée à la recette, avec la part qui reste à son rôle. */
export function depuisMatiere(m: Matiere, pourcentage: number): LigneSaisie {
  return {
    matiere_id: m.id,
    reference: m.reference,
    nature: m.composition_libelle ?? m.composition ?? '',
    designation: m.designation,
    fournisseur: m.fournisseur ?? '',
    role_id: m.role_id,
    pourcentage,
    densite: m.densite,
    prix_kg: m.prix_kg,
    prix: m.prix,
    unite_prix: m.unite_prix,
    devise: m.devise,
    disparue: false,
  }
}

export function versFormeQualite(q: QualiteFiche | null): FormeQualite {
  return {
    code: q?.code ?? '',
    nom: q?.nom ?? '',
    actif: q?.actif ?? true,
    poids: Object.fromEntries((q?.poids ?? []).map((p) => [p.role_id, p.poids])),
    lignes: (q?.recette ?? []).map(depuisFiche),
  }
}

/** Les poids non nuls (les nuls ne s'enregistrent pas, P7-5). */
export function poidsEnvoyes(f: FormeQualite) {
  return Object.entries(f.poids)
    .filter(([, p]) => p != null && p > 0)
    .map(([role_id, poids]) => ({ role_id: Number(role_id), poids: poids ?? 0 }))
}

const lignesDe = (f: FormeQualite) =>
  f.lignes.filter((l) => !l.disparue).map((l) => ({ matiere_id: l.matiere_id, pourcentage: l.pourcentage }))

/** La recette change-t-elle (lignes, parts, ou matière disparue à retirer) ? */
export function recetteChangee(f: FormeQualite, initiale: FormeQualite): boolean {
  return (
    f.lignes.some((l) => l.disparue) || JSON.stringify(lignesDe(f)) !== JSON.stringify(lignesDe(initiale))
  )
}

export function corpsQualite(f: FormeQualite, initiale: FormeQualite, version: number): QualiteCorps {
  return {
    code: f.code.trim(),
    nom: f.nom.trim(),
    actif: f.actif,
    poids: poidsEnvoyes(f),
    version,
    recette: recetteChangee(f, initiale) ? lignesDe(f) : null,
    motif: '',
  }
}

export function memeQualite(a: FormeQualite, b: FormeQualite): boolean {
  const cle = (f: FormeQualite) =>
    JSON.stringify({ c: f.code.trim(), n: f.nom.trim(), a: f.actif, p: poidsEnvoyes(f), l: lignesDe(f) })
  return cle(a) === cle(b)
}
