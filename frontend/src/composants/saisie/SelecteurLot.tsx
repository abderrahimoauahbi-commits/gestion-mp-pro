/**
 * Choisir un lot d'une matière **présent à la date** dans un magasin (`GET lots/disponibles`,
 * API 111) : le serveur les rend dans l'ordre FIFO, hors quarantaine ; l'écran garde cet ordre et
 * écarte par sûreté un lot marqué en quarantaine. Tant que la matière n'est pas choisie, le
 * sélecteur le dit.
 */
import { date, kg } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { Selecteur, type OptionSelecteur } from './Selecteur'

/** Un lot disponible (type provisoire, remplacé par `Schema<'LotDisponible'>` à la publication). */
export interface LotDisponible {
  id: number
  numero: string
  reste_kg: number
  date_entree?: string | null
  magasin?: string | null
  quarantaine?: boolean
}

export interface SelecteurLotProps {
  matiere: number | null
  date: string
  magasin: number | null
  valeur: number | null
  onChange: (id: number | null, lot?: LotDisponible) => void
  libelle?: string
}

/** Les options d'un sélecteur de lots, dans l'ordre FIFO reçu, quarantaine écartée. */
export function optionsDeLots(lots: readonly LotDisponible[]): OptionSelecteur[] {
  return lots
    .filter((l) => !l.quarantaine)
    .map((l) => ({
      id: l.id,
      titre: l.numero,
      sous: [
        `${kg(l.reste_kg)} restants`,
        l.date_entree ? `entré le ${date(l.date_entree)}` : '',
        l.magasin ?? '',
      ]
        .filter(Boolean)
        .join(' · '),
    }))
}

export function SelecteurLot({
  matiere,
  date: jour,
  magasin,
  valeur,
  onChange,
  libelle = 'Lot',
}: SelecteurLotProps) {
  const pret = matiere != null && magasin != null && jour !== ''
  const lots = useLecture<LotDisponible[]>(pret ? '/lots/disponibles' : null, {
    matiere,
    date: jour,
    magasin,
  })
  if (!pret) {
    return (
      <Selecteur
        valeur={null}
        options={[]}
        onChange={() => {}}
        libelle={libelle}
        desactive
        placeholder="Choisir d’abord la matière, la date et le magasin"
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
      vide="Aucun lot de cette matière n’est présent à cette date dans ce magasin."
      onChange={(id) =>
        onChange(
          id,
          liste.find((l) => l.id === id),
        )
      }
    />
  )
}
