/**
 * Les six indicateurs du Cockpit, **tels que le serveur les envoie** (route 209, `kpi[]`) : valeur,
 * unité, détail, formule, lien, ton. L'écran ne recalcule rien (LOTS F1) : il met la valeur en forme
 * selon son unité, pose la formule dans la bulle « ? » et ouvre l'écran qui la détaille (P1-27).
 * La valeur du stock y est celle de la Valorisation (E-06), fil sur les métiers compris.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { SUR_LES_METIERS } from '../../lib/aide'
import { permis } from '../../lib/droits'
import { INSECABLE, jours, montant, montantCourt, nombre, part } from '../../lib/format'
import { useSession } from '../../lib/session'
import type { Ton } from '../../lib/statuts'
import type { KpiServeur } from '../accueil/types'

const TONS: readonly Ton[] = ['ok', 'attention', 'urgent', 'critique', 'rupture', 'neutre', 'accent']

/** Le ton reçu, s'il est connu (sinon neutre). */
export const tonDe = (t: string): Ton => TONS.find((x) => x === t) ?? 'neutre'

/** La valeur reçue, mise en forme selon son unité ; l'unité dite à part quand elle n'y est pas. */
export function valeurKpi(k: KpiServeur): { valeur: string; unite?: string; exact?: string } {
  if (/^[A-Z]{3}$/.test(k.unite))
    return { valeur: montantCourt(k.valeur, k.unite), exact: montant(k.valeur, k.unite) }
  if (k.unite === 'j') return { valeur: jours(k.valeur) }
  if (k.unite === 'fraction') return { valeur: part(k.valeur, 0) }
  if (k.unite === '×') return { valeur: `${nombre(k.valeur, 2)}${INSECABLE}×` }
  return { valeur: nombre(k.valeur, 0, 2), unite: k.unite || undefined }
}

export function IndicateursCockpit({ kpi }: { kpi: readonly KpiServeur[] }) {
  const { role } = useSession()
  return (
    <Indicateurs libelle="Indicateurs du Cockpit">
      {kpi.map((k) => {
        const v = valeurKpi(k)
        return (
          <Kpi
            key={k.cle}
            titre={k.libelle}
            valeur={v.valeur}
            unite={v.unite}
            exact={v.exact}
            formule={k.cle === 'valeur' ? `${k.formule}. ${SUR_LES_METIERS}` : k.formule}
            detail={k.detail}
            ton={tonDe(k.ton)}
            lien={k.lien && permis(role, k.lien) ? k.lien : undefined}
          />
        )
      })}
    </Indicateurs>
  )
}
