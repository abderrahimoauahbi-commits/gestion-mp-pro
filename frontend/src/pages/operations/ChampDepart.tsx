/**
 * Le « Dépôt de départ » de l'encart de ligne : un critère de recherche facultatif qui, posé,
 * fait voir dans le choix de lot tous les lots d'un magasin, toutes matières (an. 2, « partir du
 * dépôt pour choisir ce qui bouge »). Montré pour les opérations qui partent d'un lot déjà en stock.
 */
import { Champ } from '../../composants/saisie/Champ'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { partDunLot } from './encart'
import type { MagasinFiche, TypeOperation } from './types'

export function ChampDepart({
  type,
  magasins,
  valeur,
  onChange,
}: {
  type: TypeOperation
  magasins: readonly MagasinFiche[]
  valeur: number | null
  onChange: (id: number | null) => void
}) {
  if (!partDunLot(type)) return null
  const actifs = magasins
    .filter((g) => g.actif)
    .map((g) => ({ id: g.id, titre: `${g.code}${g.type === 'quarantaine' ? ' (quarantaine)' : ''}` }))
  return (
    <Champ libelle="Dépôt de départ" aide="pour voir ce qu’il y a là-bas et choisir ce qui bouge">
      <Selecteur valeur={valeur} options={actifs} onChange={onChange} placeholder="Tous les dépôts" />
    </Champ>
  )
}
