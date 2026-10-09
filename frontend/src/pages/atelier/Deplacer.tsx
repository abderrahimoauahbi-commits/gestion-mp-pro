/**
 * Déplacer un lot (`/atelier/deplacer`) : quel lot ? (recherche sans accents, ou le QR de
 * l'étiquette) ; `?lot=ID` ouvre le déplacement (`DeplacerSaisie`).
 */
import { useNavigate, useSearchParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { ScanQR } from '../../composants/atelier/ScanQR'
import { Champ } from '../../composants/saisie/Champ'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { kgEtMetres } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { attente, NoteAtelier } from './briques'
import styles from './atelier.module.css'
import { DeplacerSaisie } from './DeplacerSaisie'
import type { LotSolde } from './types'

/** Les lots qu'on peut déplacer : de la matière disponible hors quarantaine. */
export function optionsDeplacables(lots: readonly LotSolde[]) {
  return lots
    .filter((l) => l.disponible > 0.001)
    .map((l) => ({
      id: l.lot_id,
      titre: `${l.reference} · lot ${l.lot}`,
      sous: `${kgEtMetres(l.disponible, l.kg_par_ml, true)} disponibles · ${l.magasins.map((m) => m.magasin).join(', ')}`,
      recherche: l.designation,
    }))
}

function ChoixLot() {
  const [, setParams] = useSearchParams()
  const naviguer = useNavigate()
  const lots = useLecture<LotSolde[]>('/lots', { non_nuls: true })
  const ouvrir = (id: number) => setParams({ lot: String(id) })
  return (
    <EcranAtelier titre="Déplacer" retour="/atelier">
      <div className={styles.pile}>
        {attente([lots], 'les lots') ?? (
          <Champ libelle="Quel lot ?">
            <Selecteur
              valeur={null}
              placeholder="Référence ou numéro de lot…"
              options={optionsDeplacables(lots.data ?? [])}
              vide="Aucun lot disponible ne correspond."
              onChange={(id) => id != null && ouvrir(id)}
            />
          </Champ>
        )}
        <NoteAtelier>Ou scannez l’étiquette de la palette, puis « Déplacer ce lot ».</NoteAtelier>
        <ScanQR onLot={(id) => void naviguer(`/atelier/deplacer?lot=${id}`)} />
      </div>
    </EcranAtelier>
  )
}

export default function Deplacer() {
  const [params] = useSearchParams()
  const lot = Number(params.get('lot')) || null
  return lot ? <DeplacerSaisie key={lot} id={lot} /> : <ChoixLot />
}
