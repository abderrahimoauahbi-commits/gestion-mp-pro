/**
 * L'état de la fiche d'un métier au bureau : la forme (réglage + fils), l'effet annoncé sur le
 * stock sur les métiers (calculé comme le serveur, poids de bobine retenu par le montage, an. 11),
 * le texte unique et les alertes 30 jours, l'enregistrement (une requête) et la suppression.
 */
import { api } from '../../lib/api'
import { useLecture } from '../../lib/requetes'
import { alertesMontage, effetDe, messageMontage, poidsRetenu, type FilPese } from '../atelier/calculMontage'
import type { MatiereMontage, MetierFiche, ResultatMontage } from '../atelier/types'
import { useFiche } from '../catalogue/useFiche'
import {
  corpsMontage,
  corpsReglage,
  egal,
  filsChanges,
  raisonEnregistrer,
  versForme,
  type FormeMetier,
} from './formeMetier'

const pese = (f: FormeMetier): FilPese[] =>
  f.fils.map((x) => ({ matiere_id: x.matiere_id, metres: x.metres ?? 0, pourcentage: x.pourcentage ?? 0 }))

export function useFicheMetier(fiche: MetierFiche, direction: boolean, onFermer: () => void) {
  const f = useFiche<MetierFiche, FormeMetier>(fiche, versForme, egal)
  const matieres = useLecture<MatiereMontage[]>('/montage/matieres')
  const metiers = useLecture<MetierFiche[]>('/metiers')
  const m = f.base ?? fiche
  const poids = (id: number) => poidsRetenu(m, matieres.data, id)
  const apres = { actif: f.forme.actif, bobines_par_metre: f.forme.bobines_par_metre ?? 0 }
  const effet = effetDe({ avant: m, apres }, pese(f.initiale), pese(f.forme), poids)
  const totalAvant = (metiers.data ?? []).filter((x) => x.actif).reduce((t, x) => t + x.sur_les_metiers, 0)
  const montage = corpsMontage(m, f.initiale, f.forme, effet)
  const enregistrer = async () => {
    if (direction)
      return f.ecrire(
        () =>
          api.put<MetierFiche>(`/metiers/${m.id}`, { ...corpsReglage(f.forme), version: m.version, montage }),
        'Enregistré : le stock sur les métiers est recalculé.',
      )
    return f.ecrire(
      () => api.put<ResultatMontage>(`/metiers/${m.id}/montage`, montage).then((r) => r.metier),
      'Enregistré : le stock sur les métiers est recalculé.',
    )
  }
  return {
    ...f,
    m,
    matieres: matieres.data,
    effet,
    filsChanges: filsChanges(f.forme, f.initiale),
    message: messageMontage(f.forme.actif, totalAvant, totalAvant + effet),
    alertes: alertesMontage({ avant: m, apres }, pese(f.initiale), pese(f.forme), matieres.data, poids),
    raison: raisonEnregistrer(f.forme, f.initiale, direction),
    enregistrer,
    supprimer: async () => {
      await f.executer(() => api.supprimer(`/metiers/${m.id}?version=${m.version}`))
      onFermer()
    },
  }
}

export type FicheMetierEtat = ReturnType<typeof useFicheMetier>
