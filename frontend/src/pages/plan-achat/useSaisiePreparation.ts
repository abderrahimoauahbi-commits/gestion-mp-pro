/**
 * L'état de la préparation : les lignes (parties de la suggestion **une seule fois** : une relecture
 * du serveur n'efface pas ce que l'acheteur a ajusté), l'en-tête du bon, et ce qui rend la saisie
 * « sale » (fermer demande alors d'abord).
 */
import { useMemo, useState } from 'react'

import { ecrirePalettesConteneur, lirePalettesConteneur } from './conteneur'
import {
  arrondirAuConditionnement,
  depuisMatiere,
  depuisServeur,
  revenirALaSuggestion,
  type LigneSaisie,
} from './calculPreparation'
import type { Edition } from './TablePreparation'
import type { Matiere, Preparation } from './types'

export function useSaisiePreparation(p: Preparation) {
  const depart = useMemo(() => p.lignes.filter((l) => l.matiere_id != null).map(depuisServeur), [p.lignes])
  const [lignes, setLignes] = useState<LigneSaisie[]>(depart)
  const [modifie, setModifie] = useState(false)
  const [livraison, setLivraison] = useState('')
  const [observations, setObservations] = useState('')
  const [prixCatalogue, setPrixCatalogue] = useState(false)
  const [parConteneur, setParConteneur] = useState(() => lirePalettesConteneur(p.fournisseur_id))
  const changer = (suite: (avant: LigneSaisie[]) => LigneSaisie[]) => {
    setModifie(true)
    setLignes(suite)
  }
  const ed: Edition = {
    modifier: (id, c) => changer((a) => a.map((l) => (l.matiere_id === id ? { ...l, ...c } : l))),
    remplacer: (id, ligne) => changer((a) => a.map((l) => (l.matiere_id === id ? ligne : l))),
    retirer: (id) => changer((a) => a.filter((l) => l.matiere_id !== id)),
  }
  const enEntete =
    <T>(poser: (v: T) => void) =>
    (v: T) => {
      setModifie(true)
      poser(v)
    }
  return {
    lignes,
    ed,
    sale: modifie,
    livraison,
    setLivraison: enEntete(setLivraison),
    observations,
    setObservations: enEntete(setObservations),
    prixCatalogue,
    setPrixCatalogue: enEntete(setPrixCatalogue),
    parConteneur,
    setParConteneur: (v: number | null) => {
      setParConteneur(v)
      ecrirePalettesConteneur(p.fournisseur_id, v)
    },
    ajouter: (m: Matiere) =>
      changer((a) => (a.some((l) => l.matiere_id === m.id) ? a : [...a, depuisMatiere(m)])),
    arrondir: () => changer(arrondirAuConditionnement),
    revenir: () => changer(() => revenirALaSuggestion(depart)),
  }
}

export type SaisiePreparation = ReturnType<typeof useSaisiePreparation>
