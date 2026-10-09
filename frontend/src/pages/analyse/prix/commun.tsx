/**
 * Ce que partagent la Matrice et les Prix payés : les cinq mouvements d'un prix face au précédent
 * (premier prix, stable, baisse, légère hausse, forte hausse — la forte hausse suit le réglage
 * `seuil_hausse_forte`, P8-4), leur légende, et les quatre indicateurs communs aux deux onglets.
 */
import { Indicateurs } from '../../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../../composants/retour/Badge'
import { Kpi } from '../../../composants/retour/Kpi'
import { formule } from '../../../lib/aide'
import { montant, montantCourt, nombre, part } from '../../../lib/format'
import type { Ton } from '../../../lib/statuts'
import styles from '../analyse.module.css'
import { useOpportunites } from '../donnees'
import type { HistoriquePrix, MatricePrix } from '../types'

export type Mouvement = 'initial' | 'stable' | 'baisse' | 'hausse' | 'forte'

export const MOUVEMENTS: Record<Mouvement, { ton: Ton; libelle: string }> = {
  initial: { ton: 'accent', libelle: 'Premier prix' },
  stable: { ton: 'neutre', libelle: 'Stable' },
  baisse: { ton: 'ok', libelle: 'Baisse' },
  hausse: { ton: 'attention', libelle: 'Légère hausse' },
  forte: { ton: 'critique', libelle: 'Forte hausse' },
}

const ORDRE: readonly Mouvement[] = ['initial', 'stable', 'baisse', 'hausse', 'forte']

export interface Seuils {
  stable: number
  forte: number
}

/** Les seuils du serveur (stable 0,5 %, forte = réglage), ou ceux par défaut. */
export function seuilsDe(s: Readonly<Record<string, number>> | undefined): Seuils {
  return { stable: s?.stable ?? 0.005, forte: s?.forte ?? 0.05 }
}

/** Le mouvement d'un prix face au précédent (variation en fraction ; `null` : premier prix). */
export function mouvement(variation: number | null | undefined, seuils: Seuils): Mouvement {
  if (variation == null) return 'initial'
  if (variation < -seuils.stable) return 'baisse'
  if (variation > seuils.forte) return 'forte'
  if (variation > seuils.stable) return 'hausse'
  return 'stable'
}

export function Legende({ seuils }: { seuils: Seuils }) {
  return (
    <div className={styles.legende}>
      {ORDRE.map((cle) => (
        <Badge key={cle} ton={MOUVEMENTS[cle].ton}>
          {MOUVEMENTS[cle].libelle}
        </Badge>
      ))}
      <span>
        prix moyen pondéré du mois · stable à ±{part(seuils.stable)} près · forte hausse au-delà de{' '}
        {part(seuils.forte, 0)}
      </span>
    </div>
  )
}

/** Les quatre indicateurs de la Matrice et des Prix payés. */
export function IndicateursPrix({ h, m }: { h: HistoriquePrix; m: MatricePrix }) {
  const seuils = seuilsDe(m.seuils)
  const o = useOpportunites().data
  return (
    <Indicateurs libelle="Indicateurs des prix">
      <Kpi
        titre="Achats enregistrés"
        valeur={nombre(h.lignes.length)}
        detail={`${montantCourt(h.total_achats_mad, 'MAD')} au total · ${nombre(m.mois.length)} mois d’historique`}
        exact={montant(h.total_achats_mad, 'MAD')}
        formule={formule('prix_achats')}
      />
      <Kpi
        titre="Hausses de prix"
        valeur={nombre(h.hausses)}
        ton={h.fortes_hausses ? 'critique' : h.hausses ? 'attention' : 'ok'}
        detail={`dont ${nombre(h.fortes_hausses)} forte(s), au-delà de ${part(seuils.forte, 0)}`}
        formule={formule('prix_hausses')}
      />
      <Kpi
        titre="Baisses obtenues"
        valeur={nombre(h.baisses)}
        ton="ok"
        detail="face au prix précédent de la même matière"
        formule={formule('prix_baisses')}
      />
      <Kpi
        titre="Opportunités d’économies"
        valeur={o ? montantCourt(o.total_mad, 'MAD') : '…'}
        exact={o ? `${montant(o.total_mad, 'MAD')} par an` : undefined}
        ton={o && o.total_mad > 0 ? 'attention' : 'ok'}
        detail={
          o
            ? `par an · ${nombre(o.lignes.length)} opportunité(s), onglet « Opportunités »`
            : 'calcul en cours'
        }
        lien="/analyse?onglet=opportunites"
        formule={formule('opportunite')}
      />
    </Indicateurs>
  )
}
