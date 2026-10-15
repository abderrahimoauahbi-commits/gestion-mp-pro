/**
 * « Mettre au rebut » un fond de lot (lot FOND-DE-LOT) : un bouton confirmé sur place, par solde
 * (lot, magasin), qui appelle `POST /lots/{id}/rebut` à la version lue du lot ; le serveur écrit
 * un ajustement « Rebut » validé sur tout le reste du lot dans ce magasin. La direction peut
 * aussi mettre au rebut au-dessus du seuil : le motif lui est demandé dans la confirmation (cinq
 * caractères au moins, la règle du serveur). Les refus du serveur sont dits tels quels.
 */
import { dire } from '../../composants/retour/Messages'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import { poidsFond, questionCourte, questionRebut, rebutPermis } from './fonds'
import type { LotSolde, OperationFiche, SoldeMagasin } from './types'

/** Un motif de rebut écrit en quelques mots : la règle du serveur (JUSTIFICATION_AJUSTEMENT). */
export const MOTIF_REBUT_MIN = 5

export function BoutonRebut({
  l,
  g,
  taille = 'petit',
  onFait,
}: {
  l: Pick<LotSolde, 'lot_id' | 'lot' | 'reference' | 'version'>
  g: SoldeMagasin
  taille?: 'normal' | 'petit' | 'atelier'
  onFait?: (o: OperationFiche) => void
}) {
  const { role } = useSession()
  const droit = rebutPermis(role, g)
  const ecrire = useEcriture((corps: unknown) => api.post<OperationFiche>(`/lots/${l.lot_id}/rebut`, corps))
  if (!droit.permis && !droit.raison) return null
  const rebuter = async (motif: string) => {
    const o = await ecrire.mutateAsync({ magasin_id: g.magasin_id, version: l.version, motif })
    dire(
      `${o.numero ?? 'Ajustement'} : ${poidsFond(g.quantite)} du lot ${l.lot} mis au rebut (« ${g.magasin} »).`,
    )
    onFait?.(o)
  }
  return (
    <Confirmer
      taille={taille}
      variante="danger"
      grise={droit.permis ? undefined : droit.raison}
      question={taille === 'petit' ? questionCourte(l, g) : questionRebut(l, g)}
      oui="Oui, mettre au rebut"
      motif={droit.motifExige ? 'exige' : undefined}
      motifMin={droit.motifExige ? MOTIF_REBUT_MIN : undefined}
      libelleMotif="Pourquoi (au-dessus du seuil de rebut)"
      exempleMotif="Fil moisi, inutilisable"
      titre={`Ajustement « Rebut » validé tout de suite : ${poidsFond(g.quantite)} dans « ${g.magasin} »`}
      attente="Mise au rebut…"
      onOui={rebuter}
    >
      {taille === 'petit' ? 'Mettre au rebut' : `Mettre au rebut (${poidsFond(g.quantite)}, ${g.magasin})`}
    </Confirmer>
  )
}
