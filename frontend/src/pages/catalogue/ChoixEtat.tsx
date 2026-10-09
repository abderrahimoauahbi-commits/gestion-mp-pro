/**
 * Le filtre d'état d'une liste du catalogue : « Actives » par défaut, « Actives et désactivées »,
 * « Désactivées ». Il vit dans l'adresse avec les autres filtres et compte pour un critère dès
 * qu'il quitte son défaut ; « Effacer les filtres » le remet aux actives.
 */
import filtres from '../../composants/tableaux/Filtres.module.css'
import { classes } from '../../composants/mise-en-page/classes'
import { lireEtat, type EtatFiche } from './etatListe'

export function ChoixEtat({
  valeur,
  onChange,
  libelles,
}: {
  valeur: string
  onChange: (v: EtatFiche | null) => void
  /** [actives, toutes, désactivées] : « Fournisseurs actifs », « Actifs et désactivés »… */
  libelles: readonly [string, string, string]
}) {
  const etat = lireEtat(valeur)
  return (
    <select
      aria-label="État"
      className={classes(filtres.filtre, etat !== 'actives' && filtres.pose)}
      value={etat}
      onChange={(e) => onChange(e.target.value === 'actives' ? null : lireEtat(e.target.value))}
    >
      <option value="actives">{libelles[0]}</option>
      <option value="toutes">{libelles[1]}</option>
      <option value="desactivees">{libelles[2]}</option>
    </select>
  )
}
