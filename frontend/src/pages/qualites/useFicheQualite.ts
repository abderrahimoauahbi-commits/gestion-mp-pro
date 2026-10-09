/**
 * Les gestes de la fiche qualité (direction) : enregistrer la fiche **et** la recette en une
 * requête (P7-8), supprimer, revenir à une version (motif exigé), recharger (R2). Après
 * l'enregistrement, l'avertissement du serveur (rôles sans matière d'une qualité arrêtée) est
 * dit (P7-7).
 */
import { dire } from '../../composants/retour/Messages'
import { api } from '../../lib/api'
import { useFiche } from '../catalogue/useFiche'
import { corpsQualite, memeQualite, versFormeQualite, type FormeQualite } from './formeQualite'
import type { LigneSaisie } from './recette'
import type { QualiteFiche } from './types'

export const ENREGISTREE = 'Qualité enregistrée : les besoins, les coûts et le plan d’achat sont recalculés.'
export const RESTAUREE =
  'Recette revenue à cette version, parts et poids au m² : une nouvelle version, signée et motivée, est enregistrée.'

export interface FicheQualiteEtat {
  base: QualiteFiche | null
  initiale: FormeQualite
  forme: FormeQualite
  maj: (modif: Partial<FormeQualite>) => void
  poser: (role_id: number, poids: number | null) => void
  changerLigne: (matiere_id: number, modif: Partial<LigneSaisie> | null) => void
  ajouter: (l: LigneSaisie) => void
  sale: boolean
  conflit: string | null
  enregistrer: () => Promise<void>
  supprimer: () => Promise<void>
  restaurer: (versionId: number, motif: string) => Promise<void>
  recharger: () => Promise<void>
}

export function useFicheQualite(fiche: QualiteFiche, onSupprimee: () => void): FicheQualiteEtat {
  const f = useFiche(fiche, versFormeQualite, memeQualite)
  const chemin = `/qualites/${f.base?.id ?? fiche.id}`
  const version = f.base?.version ?? fiche.version
  const apres = (q: QualiteFiche | null, message: string) => {
    if (!q) return
    dire(message)
    if (q.avertissement) dire(q.avertissement, 'attention')
  }
  return {
    base: f.base,
    initiale: f.initiale,
    forme: f.forme,
    maj: f.maj,
    poser: (role_id, poids) => f.maj({ poids: { ...f.forme.poids, [role_id]: poids } }),
    changerLigne: (id, modif) =>
      f.maj({
        lignes: modif
          ? f.forme.lignes.map((l) => (l.matiere_id === id ? { ...l, ...modif } : l))
          : f.forme.lignes.filter((l) => l.matiere_id !== id),
      }),
    ajouter: (l) => f.maj({ lignes: [...f.forme.lignes, l] }),
    sale: f.sale,
    conflit: f.conflit,
    enregistrer: async () =>
      apres(
        await f.ecrire(() => api.put<QualiteFiche>(chemin, corpsQualite(f.forme, f.initiale, version)), ''),
        ENREGISTREE,
      ),
    supprimer: async () => {
      await f.executer(() => api.supprimer(`${chemin}?version=${version}`))
      dire(`Qualité « ${f.base?.code ?? fiche.code} » supprimée.`)
      onSupprimee()
    },
    restaurer: async (vid, motif) =>
      apres(
        await f.ecrire(
          () => api.post<QualiteFiche>(`${chemin}/versions/${vid}/restaurer`, { motif, version }),
          '',
        ),
        RESTAUREE,
      ),
    recharger: () => f.recharger(() => api.get<QualiteFiche>(chemin)),
  }
}
