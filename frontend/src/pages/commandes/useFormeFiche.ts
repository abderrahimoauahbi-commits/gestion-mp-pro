/**
 * Une saisie posée sur une fiche relue par le serveur (volets Lignes, Prix, Expédition) : la forme
 * part de la fiche ; une relecture (toutes les 15 s, au retour sur l'onglet, après un geste) la
 * remet à jour **tant qu'on n'a rien saisi**, et ne l'écrase jamais sinon. La version envoyée est
 * celle de la fiche d'où la saisie est partie : si quelqu'un a changé le bon entre-temps, le
 * serveur refuse (409) et la fiche le dit, avec « Recharger ».
 */
import { useEffect, useState } from 'react'

import type { CommandeFiche } from './types'

export interface FormeFiche<F, T extends { version: number } = CommandeFiche> {
  forme: F
  /** La forme de départ (celle de la fiche lue). */
  initiale: F
  maj: (modif: Partial<F>) => void
  poser: (f: F) => void
  sale: boolean
  /** La version de la fiche d'où la saisie est partie. */
  version: number
  /** Repartir de la fiche lue (abandon des changements). */
  reprendre: () => void
  /** Repartir de la fiche rendue par une écriture. */
  repartir: (t: T) => void
}

export function useFormeFiche<T extends { version: number }, F>(
  fiche: T,
  versForme: (t: T) => F,
  egal: (a: F, b: F) => boolean,
): FormeFiche<F, T> {
  const [base, setBase] = useState(() => ({ version: fiche.version, forme: versForme(fiche) }))
  const [forme, setForme] = useState(base.forme)
  const sale = !egal(forme, base.forme)
  const repartir = (t: T) => {
    const f = versForme(t)
    setBase({ version: t.version, forme: f })
    setForme(f)
  }
  useEffect(() => {
    if (fiche.version === base.version || sale) return
    const f = versForme(fiche)
    setBase({ version: fiche.version, forme: f })
    setForme(f)
  }, [fiche, base.version, sale, versForme])
  return {
    forme,
    initiale: base.forme,
    maj: (modif) => setForme((f) => ({ ...f, ...modif })),
    poser: setForme,
    sale,
    version: base.version,
    reprendre: () => repartir(fiche),
    repartir,
  }
}

/** Deux formes simples sont égales si elles s'écrivent pareil. */
export const memeForme = <F>(a: F, b: F) => JSON.stringify(a) === JSON.stringify(b)
