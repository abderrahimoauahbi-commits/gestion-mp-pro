/**
 * Les indicateurs du plan d'achat (ECRANS-PRO 4.1), lus tels que le serveur les compte : chacun
 * avec sa formule (`aide.json`), et les ruptures disent leur périmètre (toutes les matières).
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { kg, montant, montantCourt, nombre } from '../../lib/format'
import type { Role } from '../../lib/types'
import { cleTier } from './libelles'
import { lienSi } from './liens'
import type { PlanAchat } from './types'

/** Le nombre de lignes d'un tier (« 🔥 TIER 1 » → TIER_1). */
export function compteTier(tiers: Record<string, number>, cle: string): number {
  return Object.entries(tiers)
    .filter(([k]) => cleTier(k) === cle)
    .reduce((s, [, n]) => s + n, 0)
}

export function IndicateursPlan({ plan, role }: { plan: PlanAchat; role: Role }) {
  const i = plan.indicateurs
  const tier1 = compteTier(i.tiers, 'TIER_1')
  const tier2 = compteTier(i.tiers, 'TIER_2')
  return (
    <Indicateurs libelle="Indicateurs du plan d’achat">
      <Kpi
        titre="Références à commander"
        valeur={nombre(i.references_a_commander)}
        formule={formule('plan_references')}
        detail={`dont ${nombre(i.references_en_alerte)} en alerte`}
        lien="/plan-achat?onglet=references"
      />
      <Kpi
        titre="Budget indicatif"
        valeur={montantCourt(i.budget_mad, 'MAD')}
        exact={montant(i.budget_mad, 'MAD')}
        formule={formule('plan_budget')}
        detail={`${kg(i.quantite_totale)} · prix catalogue`}
      />
      <Kpi
        titre="Références classe A"
        valeur={nombre(i.references_classe_a)}
        formule={formule('abc')}
        detail="à commander"
        lien="/plan-achat?onglet=references&abc=A"
      />
      <Kpi
        titre="Ruptures"
        valeur={nombre(i.ruptures)}
        formule={formule('plan_ruptures')}
        ton={i.ruptures ? 'rupture' : 'ok'}
        detail={`sur toutes les matières · ${nombre(i.critiques)} crit. · ${nombre(i.urgents)} urg. · ${nombre(i.attentions)} ATTENTION`}
        lien={lienSi(role, '/stock?onglet=matieres&statut=rupture') ?? undefined}
      />
      <Kpi
        titre="À émettre cette semaine"
        valeur={nombre(tier1)}
        formule={formule('plan_tier1')}
        ton={tier1 ? 'critique' : 'ok'}
        detail={`${nombre(tier2)} sous 7 jours`}
        lien="/plan-achat?onglet=references&priorite=Tier%201"
      />
    </Indicateurs>
  )
}
