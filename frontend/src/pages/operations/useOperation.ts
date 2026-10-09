/**
 * L'état et les gestes de la fenêtre d'une opération : le brouillon local (lu, ou nouveau), ce qui
 * le rend modifiable (droit du type, brouillon), les motifs proposés au rôle, les blocages
 * (calculés au serveur pour un brouillon enregistré tel quel ; suspension, dépassement et
 * quarantaine revérifiés ici dès la saisie), et les écritures (enregistrer, valider — en une
 * transaction pour un nouveau document —, supprimer, annuler).
 */
import { useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { api } from '../../lib/api'
import { ajouterJours, aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import {
  corpsOperation,
  depassements,
  incompatibilite,
  manqueOperation,
  saisieDe,
  suspensions,
  type LigneSaisie,
  type SaisieOperation,
} from './saisie'
import {
  peutSaisir,
  type MagasinFiche,
  type MotifLu,
  type Motifs,
  type OperationFiche,
  type TypeOperation,
} from './types'

export interface Donnees {
  motifs: Motifs
  magasins: MagasinFiche[]
}

/** Les motifs d'un type que ce rôle peut choisir (« Libération de quarantaine » : direction, achats). */
export function motifsPermis(motifs: Motifs, type: TypeOperation, role: string): MotifLu[] {
  return motifs.motifs.filter(
    (m) => m.type === type && (!m.impose_role || role === 'direction' || m.impose_role === role),
  )
}

/** Le brouillon local et ce qu'on en dit. */
export function useOperation(d: Donnees, op: OperationFiche | null, type: TypeOperation) {
  const { role, contexte } = useSession()
  const [s, setS] = useState<SaisieOperation>(() =>
    op
      ? saisieDe(op, d.magasins)
      : { type, date: aujourdhui(), motif_id: null, commentaire: '', ordre_id: null, lignes: [] },
  )
  const [modifie, setModifie] = useState(false)
  const poser = (modif: Partial<SaisieOperation>) => {
    setModifie(true)
    setS((x) => ({ ...x, ...modif }))
  }
  const motif = d.motifs.motifs.find((m) => m.id === s.motif_id)
  const modifiable = op ? op.statut === 'brouillon' && op.peut_agir : peutSaisir(d.motifs, s.type, role)
  const min = contexte.date_cloture ? ajouterJours(contexte.date_cloture, 1) : undefined
  const locaux = [
    ...s.lignes.map((l) => incompatibilite(l, s.type, motif)).filter(Boolean),
    ...suspensions(s.lignes, contexte.inventaires_ouverts, d.magasins),
    ...depassements(s),
  ]
  const blocages = [...new Set([...(op && !modifie ? op.blocages : []), ...locaux])]
  return {
    s,
    poser,
    modifie,
    motif,
    modifiable,
    min,
    blocages,
    manque: modifiable ? manqueOperation(s, motif, min) : [],
    motifs: motifsPermis(d.motifs, s.type, role),
    poserLigne: (l: LigneSaisie) => {
      const autres = s.lignes.filter((x) => x.cle !== l.cle)
      const i = s.lignes.findIndex((x) => x.cle === l.cle)
      poser({ lignes: i < 0 ? [...autres, l] : s.lignes.map((x) => (x.cle === l.cle ? l : x)) })
    },
    retirer: (l: LigneSaisie) => poser({ lignes: s.lignes.filter((x) => x.cle !== l.cle) }),
  }
}

/** Les écritures de la fenêtre. */
export function useGestesOperation(
  op: OperationFiche | null,
  s: SaisieOperation,
  modifie: boolean,
  apres: { cree: (o: OperationFiche) => void; supprime: () => void },
) {
  const ecrire = useEcriture(async (faire: () => Promise<OperationFiche | undefined>) => faire())
  const enregistrerSeul = () =>
    op
      ? api.put<OperationFiche>(`/operations/${op.id}`, { ...corpsOperation(s), version: op.version })
      : api.post<OperationFiche>('/operations', corpsOperation(s))
  return {
    enregistrer: async () => {
      const o = await ecrire.mutateAsync(enregistrerSeul)
      dire('Brouillon enregistré : le stock ne bouge qu’à la validation.')
      if (!op && o) apres.cree(o)
    },
    valider: async () => {
      const o = await ecrire.mutateAsync(async () => {
        if (!op) return api.post<OperationFiche>('/operations', { ...corpsOperation(s), valider: true })
        const lue = modifie ? await enregistrerSeul() : op
        return api.post<OperationFiche>(`/operations/${op.id}/valider`, { version: lue.version })
      })
      dire(`${o?.numero ?? ''} validée : le stock est à jour.`)
      if (!op && o) apres.cree(o)
    },
    supprimer: async () => {
      if (!op) return
      await ecrire.mutateAsync(async () => {
        await api.supprimer(`/operations/${op.id}?version=${op.version}`)
        return undefined
      })
      dire('Brouillon supprimé.')
      apres.supprime()
    },
    annuler: async () => {
      if (!op) return
      await ecrire.mutateAsync(() =>
        api.post<OperationFiche>(`/operations/${op.id}/annuler`, { version: op.version, motif: '' }),
      )
      dire(`${op.numero ?? ''} annulée.`)
    },
  }
}
