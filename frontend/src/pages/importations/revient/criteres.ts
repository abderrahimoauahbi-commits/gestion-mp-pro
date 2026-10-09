/**
 * Ce que vaut chaque critère pour une matière, **dans le langage du serveur d'analyse** (le filtre
 * compare ces textes), et les listes liées qu'on en tire : chaque liste ne propose que les
 * valeurs des matières qui passent les autres critères, avec leur nombre, en tri naturel.
 */
import { optionsLiees, type Filtre, type OptionFiltre } from '../../../composants/tableaux/filtrage'
import type { Schema } from '../../../lib/types'
import { CRITERES, type Critere } from './etat'

export type Matiere = Schema<'MatiereResume'>
export type Classification = Schema<'Classification'>

/** Le titrage de chaque fiche de classification (son identifiant → sa valeur, « 1500 »). */
export function titragesDe(classification: Classification | undefined): Map<number, string> {
  return new Map((classification?.titrages ?? []).map((t) => [t.id, t.valeur || t.code]))
}

/** La valeur d'un critère pour une matière ('' si elle n'en a pas). */
export function valeurCritere(m: Matiere, critere: Critere, titrages: ReadonlyMap<number, string>): string {
  switch (critere) {
    case 'composition':
      return m.composition || m.composition_libelle || ''
    case 'type_fil':
      return m.type_fil ?? ''
    case 'titrage':
      return m.titrage_id != null ? (titrages.get(m.titrage_id) ?? m.titrage ?? '') : ''
    case 'couleur':
      return m.couleur_libelle || m.couleur || m.designation
    case 'fournisseur':
      return m.fournisseur ?? ''
  }
}

/** Les cinq critères en filtres de liste sur les matières. */
export function filtresMatieres(titrages: ReadonlyMap<number, string>): Filtre<Matiere>[] {
  return CRITERES.map((c) => ({
    cle: c.cle,
    libelle: c.libelle,
    valeur: (m: Matiere) => valeurCritere(m, c.cle, titrages),
  }))
}

/** Les options liées de chaque critère, en tri naturel. */
export function optionsDesCriteres(
  matieres: readonly Matiere[],
  titrages: ReadonlyMap<number, string>,
  criteres: Record<Critere, string>,
): Record<Critere, OptionFiltre[]> {
  const filtres = filtresMatieres(titrages)
  const sortie: Record<Critere, OptionFiltre[]> = {
    composition: [],
    type_fil: [],
    titrage: [],
    couleur: [],
    fournisseur: [],
  }
  for (const f of filtres) {
    const critere = CRITERES.find((c) => c.cle === f.cle)?.cle
    if (critere) sortie[critere] = optionsLiees(matieres, filtres, criteres, f)
  }
  return sortie
}

/** Le titrage d'une ligne regroupée (« 1500 den ») : son premier mot, celui du filtre. */
export const premierMot = (valeur: string) => valeur.trim().split(/\s+/)[0] ?? ''
