/**
 * Les référentiels de l'analyse : les matières (`GET matieres`), la classification
 * (`GET classification`, pour la valeur des titrages) et les qualités (`GET qualites`), mis en
 * options de sélecteur, en listes liées et en liens (référence → fiche matière).
 */
import { useMemo } from 'react'

import type { OptionSelecteur } from '../../../composants/saisie/Selecteur'
import { permis } from '../../../lib/droits'
import { useLecture } from '../../../lib/requetes'
import { useSession } from '../../../lib/session'
import type { Schema } from '../../../lib/types'
import { optionsDesCriteres, titragesDe, valeurCritere, type Classification, type Matiere } from './criteres'
import type { Critere } from './etat'

type Qualite = Schema<'QualiteResume'>

/** Une option par matière : référence, puis fournisseur, titrage et couleur ; tout est cherché. */
function optionMatiere(m: Matiere, titrages: ReadonlyMap<number, string>): OptionSelecteur {
  const titrage = valeurCritere(m, 'titrage', titrages)
  const couleur = valeurCritere(m, 'couleur', titrages)
  return {
    id: m.id,
    titre: m.reference,
    sous: [m.fournisseur, titrage, couleur].filter(Boolean).join(' · ') || undefined,
    recherche: [m.designation, valeurCritere(m, 'composition', titrages), m.type_fil]
      .filter(Boolean)
      .join(' '),
  }
}

export function useReferentiels(criteres: Record<Critere, string>) {
  const { role } = useSession()
  const matieres = useLecture<Matiere[]>('/matieres')
  const classification = useLecture<Classification>('/classification')
  const qualites = useLecture<Qualite[]>('/qualites')
  const titrages = useMemo(() => titragesDe(classification.data), [classification.data])
  const liste = useMemo(() => matieres.data ?? [], [matieres.data])
  const options = useMemo(() => optionsDesCriteres(liste, titrages, criteres), [liste, titrages, criteres])
  const optionsMatieres = useMemo(() => liste.map((m) => optionMatiere(m, titrages)), [liste, titrages])
  const optionsQualites = useMemo<OptionSelecteur[]>(
    () => (qualites.data ?? []).map((q) => ({ id: q.id, titre: q.nom ? `${q.code} — ${q.nom}` : q.code })),
    [qualites.data],
  )
  const parReference = useMemo(() => new Map(liste.map((m) => [m.reference, m.id])), [liste])
  const ouvreMatiere = permis(role, '/matieres/1')
  return {
    options,
    optionsMatieres,
    optionsQualites,
    /** La référence d'une matière choisie (son n° si elle n'est pas encore lue). */
    reference: (id: number) => liste.find((m) => m.id === id)?.reference ?? `n° ${id}`,
    /** L'identifiant de la matière d'une référence, si le rôle ouvre sa fiche. */
    matiere: (reference: string) => (ouvreMatiere ? parReference.get(reference) : undefined),
  }
}
