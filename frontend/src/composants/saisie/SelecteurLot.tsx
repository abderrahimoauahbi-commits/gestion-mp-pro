/**
 * Choisir un lot d'une matière **présent à la date** (`GET lots/disponibles`, API 111, forme
 * `LotDisponible` : une ligne par lot et magasin) : le serveur les rend dans l'ordre FIFO, hors
 * quarantaine ; l'écran garde cet ordre. Le magasin est facultatif (route 111) : sans lui, un lot
 * présent dans deux magasins n'est proposé qu'une fois, ses quantités ajoutées et ses magasins
 * nommés. Tant que la matière n'est pas choisie, le sélecteur le dit.
 */
import { date, kg } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { Selecteur, type OptionSelecteur } from './Selecteur'

export type LotDisponible = Schema<'LotDisponible'>

export interface SelecteurLotProps {
  matiere: number | null
  date: string
  /** Le magasin d'où le lot part ; `null` : tous les magasins. */
  magasin: number | null
  valeur: number | null
  /** Le lot choisi, et ses lignes (une par magasin). */
  onChange: (id: number | null, lignes?: readonly LotDisponible[]) => void
  libelle?: string
}

/** Les options d'un sélecteur de lots, dans l'ordre FIFO reçu, un lot une seule fois. */
export function optionsDeLots(lignes: readonly LotDisponible[]): OptionSelecteur[] {
  const ordre: number[] = []
  const parLot = new Map<number, LotDisponible[]>()
  for (const l of lignes) {
    if (!parLot.has(l.lot_id)) ordre.push(l.lot_id)
    parLot.set(l.lot_id, [...(parLot.get(l.lot_id) ?? []), l])
  }
  return ordre.map((id) => {
    const ls = parLot.get(id) ?? []
    const [premier] = ls
    const reste = ls.reduce((t, l) => t + l.quantite, 0)
    return {
      id,
      titre: premier?.lot ?? '',
      sous: [
        `${kg(reste)} restants`,
        premier ? `entré le ${date(premier.entre_le)}` : '',
        ls.map((l) => l.magasin).join(', '),
      ]
        .filter(Boolean)
        .join(' · '),
    }
  })
}

export function SelecteurLot({
  matiere,
  date: jour,
  magasin,
  valeur,
  onChange,
  libelle = 'Lot',
}: SelecteurLotProps) {
  const pret = matiere != null && jour !== ''
  const lots = useLecture<LotDisponible[]>(pret ? '/lots/disponibles' : null, {
    matiere,
    date: jour,
    magasin: magasin ?? undefined,
  })
  if (!pret) {
    return (
      <Selecteur
        valeur={null}
        options={[]}
        onChange={() => {}}
        libelle={libelle}
        desactive
        placeholder="Choisir d’abord la matière et la date"
      />
    )
  }
  if (lots.isPending) return <Chargement quoi="les lots disponibles" />
  if (lots.isError) return <Erreur erreur={lots.error} onReessayer={() => void lots.refetch()} />
  const liste = lots.data
  return (
    <Selecteur
      valeur={valeur}
      options={optionsDeLots(liste)}
      libelle={libelle}
      vide={
        magasin == null
          ? 'Aucun lot de cette matière n’est présent à cette date.'
          : 'Aucun lot de cette matière n’est présent à cette date dans ce magasin.'
      }
      onChange={(id) =>
        onChange(
          id,
          liste.filter((l) => l.lot_id === id),
        )
      }
    />
  )
}
