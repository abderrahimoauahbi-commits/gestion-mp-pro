/**
 * Le socle commun des fiches versionnées du lot (matière, fournisseur, qualité) : la fiche lue
 * (`base`), la forme de départ et la forme saisie (`sale` = elles diffèrent), et l'écriture qui
 * garde le conflit de version **sur la fiche** (R2) au lieu d'un toast : la saisie reste, le
 * message du serveur s'affiche avec « Recharger la fiche ». Une écriture réussie relit tout
 * (invalidation globale) et repart de la fiche rendue par le serveur.
 */
import { useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { useEcriture } from '../../lib/requetes'
import { messageConflit, RECHARGEE } from './Conflit'

export interface Fiche<T, F> {
  base: T | null
  initiale: F
  forme: F
  maj: (modif: Partial<F>) => void
  sale: boolean
  conflit: string | null
  /** Écrit et repart de la fiche rendue (qu'il rend) ; `null` si la version était périmée (conflit affiché). */
  ecrire: (envoi: () => Promise<T>, message: string, garder?: (avant: F, apres: F) => F) => Promise<T | null>
  /** Une écriture sans fiche en retour (suppression) : refus dits par l'appelant. */
  executer: (envoi: () => Promise<unknown>) => Promise<unknown>
  repartir: (t: T, garder?: (avant: F, apres: F) => F) => void
  recharger: (lire: () => Promise<T>) => Promise<void>
  /** La forme saisie devient la forme de départ (une création qui s'en va ailleurs). */
  oublier: () => void
}

export function useFiche<T, F>(
  fiche: T | null,
  versForme: (t: T | null) => F,
  egal: (a: F, b: F) => boolean,
): Fiche<T, F> {
  const [base, setBase] = useState(fiche)
  const [initiale, setInitiale] = useState(() => versForme(fiche))
  const [forme, setForme] = useState(initiale)
  const [conflit, setConflit] = useState<string | null>(null)
  const ecriture = useEcriture((envoi: () => Promise<T>) => envoi())
  const autre = useEcriture((envoi: () => Promise<unknown>) => envoi())
  const repartir = (t: T, garder?: (avant: F, apres: F) => F) => {
    const f = versForme(t)
    setBase(t)
    setInitiale(f)
    setForme((avant) => (garder ? garder(avant, f) : f))
    setConflit(null)
  }
  return {
    base,
    initiale,
    forme,
    maj: (modif) => setForme((f) => ({ ...f, ...modif })),
    sale: !egal(forme, initiale),
    conflit,
    ecrire: async (envoi, message, garder) => {
      let t: T
      try {
        t = await ecriture.mutateAsync(envoi)
      } catch (e) {
        const m = messageConflit(e)
        if (!m) throw e
        setConflit(m)
        return null
      }
      repartir(t, garder)
      if (message) dire(message)
      return t
    },
    executer: (envoi) => autre.mutateAsync(envoi),
    repartir,
    recharger: async (lire) => {
      repartir(await lire())
      dire(RECHARGEE, 'info')
    },
    oublier: () => setInitiale(forme),
  }
}
