/**
 * Les indicateurs de la production : les douze mois à venir, le mois en cours (tissé face au prévu
 * et au temps écoulé), l'écart au plan des mois clos (cliquable vers « Plan et réalisé »), la matière
 * nécessaire sur douze mois (cliquable vers « Besoins matière »). Masqués sur l'onglet des besoins.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { kg, m2, nombre, part, partSignee, VIDE } from '../../lib/format'
import { decouper } from '../../lib/heure'
import { ecartClos, somme, tonEcartPlan, type PlanEtRealise, type PlanProduction } from './plan'

/** La part du mois écoulée à la date de référence (le 15 octobre : 15 / 31). */
export function prorata(dateReference: string): number {
  const lu = decouper(dateReference)
  if (!lu) return 0
  const { annee, mois, jour } = lu.mur
  return jour / new Date(Date.UTC(annee, mois, 0)).getUTCDate()
}

/** Les chiffres des indicateurs, lus dans le plan et le réalisé. */
export function chiffresProduction(plan: PlanProduction, realise: PlanEtRealise | undefined) {
  const codes = new Set(plan.qualites.map((q) => q.code))
  const prevuM0 = somme(plan.qualites.map((q) => q.glissant[0] ?? 0))
  const tisseM0 =
    somme(plan.qualites.map((q) => q.tisse_mois_en_cours)) +
    somme(plan.tisse_hors_plan.filter((x) => !codes.has(x.qualite)).map((x) => x.m2))
  return {
    auPlan: plan.qualites.filter((q) => q.total_glissant > 0).length,
    total: somme(plan.qualites.map((q) => q.total_glissant)),
    prevuM0,
    tisseM0,
    ecoule: prorata(plan.date_reference),
    avancement: prevuM0 ? tisseM0 / prevuM0 : null,
    matiere: somme(plan.qualites.map((q) => q.total_glissant * q.kg_m2)),
    clos: realise ? ecartClos(realise) : null,
  }
}

function KpiEcart({ clos }: { clos: ReturnType<typeof ecartClos> | null }) {
  let detail = 'chargement'
  if (clos)
    detail = clos.mois
      ? `${m2(clos.fait)} tissés pour ${m2(clos.prevu)} prévus (${clos.mois} mois)`
      : 'pas encore de mois clos depuis la mise en service'
  return (
    <Kpi
      titre="Écart au plan, mois clos"
      valeur={!clos ? '…' : clos.mois && clos.ecart != null ? partSignee(clos.ecart) : VIDE}
      detail={detail}
      ton={tonEcartPlan(clos?.ecart)}
      lien="/production?onglet=realise"
      formule={formule('ecart_plan')}
    />
  )
}

export function IndicateursProduction({
  plan,
  realise,
}: {
  plan: PlanProduction
  realise: PlanEtRealise | undefined
}) {
  const c = chiffresProduction(plan, realise)
  return (
    <Indicateurs>
      <Kpi
        titre="Plan des douze mois à venir"
        valeur={m2(c.total)}
        detail={`${m2(c.total / 12)} par mois en moyenne · ${c.auPlan} qualité(s)`}
        formule={formule('plan_glissant')}
      />
      <Kpi
        titre="Mois en cours"
        valeur={m2(c.tisseM0)}
        detail={
          c.prevuM0
            ? `tissés sur ${nombre(c.prevuM0)} prévus (${part(c.avancement, 0)}) · ${part(c.ecoule, 0)} du mois écoulé`
            : 'aucun plan ce mois-ci'
        }
        ton={
          c.avancement != null && c.ecoule > 0.2 && c.avancement < c.ecoule - 0.15 ? 'attention' : undefined
        }
        formule={formule('mois_en_cours')}
      />
      <KpiEcart clos={c.clos} />
      <Kpi
        titre="Matière nécessaire sur douze mois"
        valeur={kg(c.matiere)}
        detail={`perte de ${nombre(plan.taux_perte * 100, 1)} % comprise`}
        lien="/production?onglet=besoins"
        formule={formule('besoin_mois')}
      />
    </Indicateurs>
  )
}
