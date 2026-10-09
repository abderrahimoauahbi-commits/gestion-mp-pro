/**
 * Les indicateurs de la fiche qualité, calculés à la frappe comme le serveur : coût matière
 * (absent pour l'alimentation), poids de la recette, état de la recette, plan (et le coût d'un
 * mois pour la direction et les achats).
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { m2, montant, nombre, prix, VIDE } from '../../lib/format'
import type { Bilan } from './recette'

export function IndicateursFiche({
  b,
  base,
  voitPrix,
  sale,
}: {
  b: Bilan
  base: number
  voitPrix: boolean
  sale: boolean
}) {
  const etat = b.faux.length
    ? { valeur: `${nombre(b.faux.length)} rôle(s) faux`, ton: 'critique' as const }
    : b.sansMatiere.length
      ? { valeur: `${nombre(b.sansMatiere.length)} rôle(s) sans matière`, ton: 'attention' as const }
      : { valeur: 'Juste', ton: 'ok' as const }
  return (
    <Indicateurs libelle="Indicateurs de la qualité">
      {voitPrix ? (
        <Kpi
          titre="Coût matière"
          valeur={b.cout_m2 == null ? VIDE : `${prix(b.cout_m2)} MAD / m²`}
          detail={sale ? 'selon la saisie, perte matière comprise' : 'perte matière comprise'}
          formule={formule('qualite_cout')}
        />
      ) : null}
      <Kpi
        titre="Poids de la recette"
        valeur={`${nombre(b.kg_m2, 4)} kg / m²`}
        detail="ce que pèsent les matières d’un m²"
        formule={formule('qualite_poids')}
      />
      <Kpi
        titre="Recette"
        valeur={etat.valeur}
        ton={etat.ton}
        detail={`${nombre(b.matieres)} matière(s) · ${nombre(b.roles)} rôle(s)`}
        formule={formule('qualite_recette')}
      />
      <Kpi
        titre="Plan"
        valeur={`${m2(base)} / mois`}
        detail={
          voitPrix && b.cout_m2 != null
            ? `coût d’un mois : ${montant(b.cout_m2 * base, 'MAD')}`
            : 'avant saisonnalité'
        }
        formule={formule('qualite_plan')}
      />
    </Indicateurs>
  )
}
