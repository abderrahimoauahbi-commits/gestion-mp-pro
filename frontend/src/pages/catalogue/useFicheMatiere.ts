/**
 * Les gestes de la fiche matière : créer, enregistrer (la fiche entière à sa version lue),
 * désactiver et réactiver (la fiche **telle qu'enregistrée**, seul l'état change : une ancienne
 * fiche incomplète se désactive sans être complétée — H-28, P7-21), supprimer, recharger. Le
 * conflit de version reste sur la fiche (`useFiche`).
 */
import { useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { memeFiche, versCorps, versForme, type DefautsCreation, type FormeMatiere } from './formeMatiere'
import type { Classification, MatiereFiche } from './types'
import { useFiche } from './useFiche'

export interface FicheMatiereEtat {
  base: MatiereFiche | null
  forme: FormeMatiere
  maj: (modif: Partial<FormeMatiere>) => void
  sale: boolean
  /** La référence a été retouchée à la main (ou la matière existe) : elle ne suit plus la composée. */
  libre: boolean
  retoucher: () => void
  conflit: string | null
  creer: () => Promise<void>
  enregistrer: () => Promise<void>
  changerEtat: (actif: boolean) => Promise<void>
  supprimer: () => Promise<void>
  recharger: () => Promise<void>
}

const garderSuffixe = (avant: FormeMatiere, apres: FormeMatiere) => ({ ...apres, suffixe: avant.suffixe })

export function useFicheMatiere({
  fiche,
  c,
  defauts,
  onCree,
  onSupprimee,
}: {
  fiche: MatiereFiche | null
  c: Classification
  defauts?: DefautsCreation
  onCree: (id: number) => void
  onSupprimee: () => void
}): FicheMatiereEtat {
  const f = useFiche(fiche, (m) => versForme(m, c, defauts), memeFiche)
  const creation = useEcriture((corps: object) => api.post<MatiereFiche>('/matieres', corps))
  const [retouchee, setRetouchee] = useState(false)
  const base = f.base
  const chemin = `/matieres/${base?.id}`
  const ecrire = async (corps: object, message: string) => {
    await f.ecrire(() => api.put<MatiereFiche>(chemin, corps), message, garderSuffixe)
  }
  return {
    base,
    forme: f.forme,
    maj: f.maj,
    sale: f.sale,
    libre: base != null || retouchee,
    retoucher: () => setRetouchee(true),
    conflit: f.conflit,
    creer: async () => {
      const r = await creation.mutateAsync(versCorps(f.forme, null))
      f.oublier()
      dire('Matière créée : elle se commande dès maintenant.')
      onCree(r.id)
    },
    enregistrer: () => ecrire({ ...versCorps(f.forme, base), version: base?.version }, 'Fiche enregistrée.'),
    changerEtat: (actif) =>
      ecrire(
        { ...versCorps(f.initiale, base), actif, version: base?.version },
        actif ? 'Matière réactivée.' : 'Matière désactivée.',
      ),
    supprimer: async () => {
      if (!base) return
      await f.executer(() => api.supprimer(`/matieres/${base.id}?version=${base.version}`))
      dire(`« ${base.reference} » supprimée.`)
      onSupprimee()
    },
    recharger: () => f.recharger(() => api.get<MatiereFiche>(chemin)),
  }
}
