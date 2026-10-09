/**
 * Libérer un lot de sa quarantaine, depuis sa fiche (direction, achats ; P1-17) : **tout** ce qui
 * est en quarantaine, une ligne par magasin de quarantaine, vers un magasin courant, après avoir
 * dit ce qui a été contrôlé. Un transfert « Libération de quarantaine » créé et validé dans une
 * seule transaction (`POST operations`, `valider: true`) : plus de brouillon à effacer si la
 * validation est refusée. Les refus du serveur sont dits tels quels.
 */
import { useEffect, useState } from 'react'

import { dire } from '../../composants/retour/Messages'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Saisie } from '../../composants/saisie/Saisie'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Carte } from '../../composants/mise-en-page/Carte'
import { api } from '../../lib/api'
import { kgEtMetres } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import { useMagasins, useMotifs } from './donnees'
import { estQuarantaine, POUSSIERE, type LotFiche, type OperationFiche } from './types'

/** Le motif imposé par le serveur pour sortir de quarantaine. */
export const MOTIF_LIBERATION = 'Libération de quarantaine'

/** L'état de la libération et son envoi. */
function useLiberation(l: LotFiche, onSale?: (sale: boolean) => void) {
  const magasins = useMagasins()
  const motifs = useMotifs()
  const [vers, setVers] = useState<number | null>(null)
  const [controle, setControle] = useState('')
  const sale = controle.trim() !== ''
  useEffect(() => onSale?.(sale), [onSale, sale])
  const ecrire = useEcriture((corps: unknown) => api.post<OperationFiche>('/operations', corps))
  const sources = l.magasins.filter((s) => estQuarantaine(s.type) && s.quantite > POUSSIERE)
  const total = sources.reduce((t, s) => t + s.quantite, 0)
  const courants = (magasins.data ?? [])
    .filter((g) => g.actif && !estQuarantaine(g.type))
    .sort((a, b) => b.kg_detenus - a.kg_detenus)
  const destination = vers ?? courants[0]?.id ?? null
  const motif = motifs.data?.motifs.find((m) => m.type === 'transfert' && m.libelle === MOTIF_LIBERATION)
  const liberer = async () => {
    const op = await ecrire.mutateAsync({
      type: 'transfert',
      date: aujourdhui(),
      motif_id: motif?.id ?? null,
      commentaire: controle.trim(),
      valider: true,
      lignes: sources.map((s) => ({
        matiere_id: l.matiere_id,
        lot_id: l.lot_id,
        magasin_id: s.magasin_id,
        magasin_destination_id: destination,
        quantite: s.quantite,
      })),
    })
    setControle('')
    dire(
      `${op.numero ?? 'Transfert'} : ${kgEtMetres(total, l.kg_par_ml)} libérés, disponibles pour les machines.`,
    )
  }
  const manque = [
    ...(controle.trim().length < 3 ? ['ce qui a été contrôlé'] : []),
    ...(destination == null ? ['la destination'] : []),
  ]
  const grise = motif || motifs.isPending ? undefined : `Le motif « ${MOTIF_LIBERATION} » est introuvable.`
  return { sources, total, courants, destination, setVers, controle, setControle, manque, grise, liberer }
}

export function Liberation({ l, onSale }: { l: LotFiche; onSale?: (sale: boolean) => void }) {
  const x = useLiberation(l, onSale)
  const total = kgEtMetres(x.total, l.kg_par_ml)
  return (
    <Carte
      titre="Libération de quarantaine"
      ton="attention"
      sous={`En quarantaine : ${x.sources.map((s) => `${kgEtMetres(s.quantite, l.kg_par_ml)} dans « ${s.magasin} »`).join(' · ')}`}
    >
      <Grille colonnes={3}>
        <Champ libelle="Vers le magasin">
          <Selecteur
            valeur={x.destination}
            options={x.courants.map((g) => ({ id: g.id, titre: g.code, sous: g.nom }))}
            onChange={(id) => x.setVers(id)}
          />
        </Champ>
        <Champ
          libelle="Ce qui a été contrôlé"
          obligatoire
          aide="Trois caractères au moins ; écrit au journal."
        >
          <Saisie
            valeur={x.controle}
            onChange={x.setControle}
            max={300}
            placeholder="Échantillon testé, couleur conforme…"
          />
        </Champ>
        <Champ libelle="Libérer">
          <Confirmer
            variante="principal"
            manque={x.manque}
            grise={x.grise}
            question={`Libérer ${total} : la matière devient disponible pour les machines ?`}
            oui="Oui, libérer"
            titre="Transfert « Libération de quarantaine », validé tout de suite"
            onOui={x.liberer}
          >
            Libérer {total}
          </Confirmer>
        </Champ>
      </Grille>
    </Carte>
  )
}
