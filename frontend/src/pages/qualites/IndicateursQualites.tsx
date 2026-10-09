/**
 * Les indicateurs de « Qualités et recettes » : qualités fabriquées, recettes incomplètes (même
 * base que la nomenclature, arrêtées à part), plan mensuel (vers le plan de production), coût
 * matière moyen pondéré par le plan (absent pour l'alimentation).
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { m2, nombre, prix } from '../../lib/format'
import { synthese } from './indicateurs'
import type { Qualite } from './types'

export function IndicateursQualites({
  qualites,
  voitPrix,
}: {
  qualites: readonly Qualite[]
  voitPrix: boolean
}) {
  const s = synthese(qualites)
  const arretees = s.incompletesArretees ? ` (arrêtées : ${nombre(s.incompletesArretees)})` : ''
  return (
    <Indicateurs libelle="Indicateurs des qualités">
      <Kpi
        titre="Qualités fabriquées"
        valeur={nombre(s.fabriquees)}
        detail={s.arretees ? `${nombre(s.arretees)} arrêtée(s)` : 'aucune arrêtée'}
        formule={formule('qualites_fabriquees')}
      />
      <Kpi
        titre="Recettes incomplètes"
        valeur={nombre(s.incompletes.length)}
        ton={s.incompletes.length ? 'critique' : 'ok'}
        detail={(s.incompletes.length ? s.incompletes.join(', ') : 'chaque rôle fait 100 %') + arretees}
        formule={formule('recettes_incompletes')}
      />
      <Kpi
        titre="Plan mensuel"
        valeur={m2(s.planMensuel)}
        detail="avant saisonnalité · le saisir"
        lien="/production?onglet=plan"
        formule={formule('plan_mensuel')}
      />
      {voitPrix ? (
        <Kpi
          titre="Coût matière moyen"
          valeur={s.coutMoyen == null ? '—' : `${prix(s.coutMoyen)} MAD / m²`}
          detail="pondéré par le plan"
          formule={formule('cout_matiere_moyen')}
        />
      ) : null}
    </Indicateurs>
  )
}
