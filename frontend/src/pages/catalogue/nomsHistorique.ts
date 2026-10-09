/**
 * Les noms des identifiants d'une matière pour son onglet Historique : « Fournisseur : HASIRCI →
 * LOMAT », « Couleur : C5N → C7 » au lieu des numéros que le journal garde. Lus dans les listes
 * que la fiche a déjà chargées (même cache) ; les codes douaniers pour direction et achats.
 */
import { useMemo } from 'react'

import type { NomsHistorique } from '../../composants/documents/libellesHistorique'
import { useClassification, useCodesDouaniers, useFournisseurs } from './donnees'

function parId<T extends { id: number }>(liste: readonly T[] | undefined, nom: (x: T) => string) {
  return new Map((liste ?? []).map((x) => [x.id, nom(x)]))
}

const code = (x: { code: string }) => x.code

/** Les noms par champ ; `voitAchat` : direction et achats (codes douaniers). */
export function useNomsMatiere(voitAchat: boolean): NomsHistorique {
  const c = useClassification().data
  const fournisseurs = useFournisseurs().data
  const codes = useCodesDouaniers(voitAchat).data
  return useMemo(
    () => ({
      role_id: parId(c?.roles, code),
      composition_id: parId(c?.compositions, code),
      type_fil_id: parId(c?.types_fil, code),
      titrage_id: parId(c?.titrages, code),
      couleur_id: parId(c?.couleurs, code),
      fournisseur_id: parId(fournisseurs, (f) => f.nom),
      code_douanier_id: parId(codes, code),
    }),
    [c, fournisseurs, codes],
  )
}
