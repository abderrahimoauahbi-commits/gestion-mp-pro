/**
 * Les indicateurs de la fiche fournisseur : matières (par devise), délai (déclaré, mesuré, et
 * pourquoi il est en attention — P7-24), livraisons parfaites (OTIF) et score, lus dans la
 * performance **par identifiant** (P7-25). Chacun dit sa formule.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { jours, nombre, part, VIDE } from '../../lib/format'
import { codeClassement, delaiDepasse } from './formeFournisseur'
import { scoreDe, usePerformance } from './performance'
import type { Fournisseur } from './types'

function detailMatieres(f: Fournisseur): string {
  const parDevise = Object.entries(f.devises)
  if (!f.nb_matieres) return 'aucune au catalogue'
  return parDevise.map(([d, n]) => `${nombre(n)} en ${d}`).join(', ')
}

export function IndicateursFournisseur({ f }: { f: Fournisseur }) {
  const perf = usePerformance()
  const s = scoreDe(perf.data, f.id)
  const depasse = delaiDepasse(f)
  return (
    <Indicateurs libelle="Indicateurs du fournisseur">
      <Kpi
        titre="Matières"
        valeur={nombre(f.nb_matieres)}
        detail={detailMatieres(f)}
        formule={formule('fournisseur_matieres')}
      />
      <Kpi
        titre="Délai"
        valeur={jours(f.delai_jours)}
        ton={depasse ? 'attention' : undefined}
        detail={
          f.delai_mesure_jours != null
            ? `mesuré ${jours(f.delai_mesure_jours)} sur ${nombre(f.livraisons_mesurees)} livraison(s)${depasse ? ' : plus de 20 % au-delà du déclaré, corriger la fiche' : ''}`
            : 'déclaré ; pas encore de livraison mesurée'
        }
        formule={formule('fournisseur_delai')}
      />
      <Kpi
        titre="Livraisons parfaites (OTIF)"
        valeur={s?.otif == null ? VIDE : part(s.otif, 0)}
        ton={s?.otif == null ? undefined : s.otif >= (perf.data?.cible_otif ?? 0) ? 'ok' : 'critique'}
        detail={s ? `${nombre(s.receptions)} réception(s) notée(s)` : 'aucune réception notée'}
        formule={formule('otif')}
      />
      <Kpi
        titre="Score"
        valeur={s?.score == null ? VIDE : `${nombre(s.score)} / 100`}
        detail={
          s?.score == null ? (
            'se calcule dès la première réception'
          ) : (
            <>
              <Badge famille="classement" valeur={codeClassement(s.classement)} /> {s.action}
            </>
          )
        }
        formule={formule('otif')}
      />
    </Indicateurs>
  )
}
