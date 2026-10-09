/**
 * Les gestes de la fiche fournisseur : créer, enregistrer (la fiche entière à sa version lue),
 * désactiver et réactiver (la fiche telle qu'enregistrée, seul l'état change), supprimer,
 * recharger. Le conflit de version reste sur la fiche (R2, P7-14 : « modifié entre-temps par… »).
 */
import { dire } from '../../composants/retour/Messages'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import {
  corpsFournisseur,
  memeFournisseur,
  versFormeFournisseur,
  type FormeFournisseur,
} from './formeFournisseur'
import type { Fournisseur } from './types'
import { useFiche } from './useFiche'

export interface FicheFournisseurEtat {
  base: Fournisseur | null
  forme: FormeFournisseur
  maj: (modif: Partial<FormeFournisseur>) => void
  sale: boolean
  conflit: string | null
  creer: () => Promise<void>
  enregistrer: () => Promise<void>
  changerEtat: (actif: boolean) => Promise<void>
  supprimer: () => Promise<void>
  recharger: () => Promise<void>
}

export function useFicheFournisseur({
  fiche,
  onCree,
  onSupprime,
}: {
  fiche: Fournisseur | null
  onCree: (id: number) => void
  onSupprime: () => void
}): FicheFournisseurEtat {
  const f = useFiche(fiche, versFormeFournisseur, memeFournisseur)
  const creation = useEcriture((corps: object) => api.post<Fournisseur>('/fournisseurs', corps))
  const base = f.base
  const chemin = `/fournisseurs/${base?.id}`
  const ecrire = async (corps: object, message: string) => {
    await f.ecrire(() => api.put<Fournisseur>(chemin, corps), message)
  }
  return {
    base,
    forme: f.forme,
    maj: f.maj,
    sale: f.sale,
    conflit: f.conflit,
    creer: async () => {
      const r = await creation.mutateAsync(corpsFournisseur(f.forme))
      f.oublier()
      dire('Fournisseur créé : ses matières peuvent maintenant le désigner.')
      onCree(r.id)
    },
    enregistrer: () => ecrire({ ...corpsFournisseur(f.forme), version: base?.version }, 'Fiche enregistrée.'),
    changerEtat: (actif) =>
      ecrire(
        { ...corpsFournisseur(f.initiale), actif, version: base?.version },
        actif ? 'Fournisseur réactivé.' : 'Fournisseur désactivé.',
      ),
    supprimer: async () => {
      if (!base) return
      await f.executer(() => api.supprimer(`/fournisseurs/${base.id}?version=${base.version}`))
      dire(`« ${base.nom} » supprimé.`)
      onSupprime()
    },
    recharger: () => f.recharger(() => api.get<Fournisseur>(chemin)),
  }
}
