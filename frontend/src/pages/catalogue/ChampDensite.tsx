/**
 * La densité d'une matière (kg par mètre) : elle ramène aux kilos un cuir, des franges, un ruban
 * (comptés en mètres dans la recette) et un prix au mètre. Bornes du serveur à la frappe.
 */
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import { BORNES_MATIERE } from './bornes'

export function ChampDensite({
  valeur,
  onChange,
  aide,
}: {
  valeur: number | null
  onChange: (v: number | null) => void
  aide: string
}) {
  return (
    <Champ libelle="Densité (kg / ml)" obligatoire aide={aide}>
      <Nombre
        valeur={valeur}
        onChange={onChange}
        min={BORNES_MATIERE.densite[0]}
        max={BORNES_MATIERE.densite[1]}
        decimales={6}
        unite="kg / ml"
      />
    </Champ>
  )
}
