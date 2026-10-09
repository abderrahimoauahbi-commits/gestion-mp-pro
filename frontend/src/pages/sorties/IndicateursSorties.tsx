/**
 * Les indicateurs des Sorties, sur les ordres affichés : leur nombre, le sorti net (ou « À sortir »
 * sur les brouillons), l'écart à la recette (un manque critique, un excès à surveiller, P2-25), et
 * les brouillons de la période (cliquable).
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { date, kg, nombre } from '../../lib/format'
import type { OrdreResume } from './donnees'
import { EcartRecette, ecartRelatif, tonEcart } from './ecart'

export function IndicateursSorties({
  affiches,
  periode,
  brouillons,
  du,
  au,
}: {
  affiches: readonly OrdreResume[]
  periode: readonly OrdreResume[]
  brouillons: boolean
  du?: string
  au?: string
}) {
  const net = affiches.reduce((t, o) => t + (brouillons ? o.total : o.net), 0)
  const revenu = affiches.reduce((t, o) => t + o.revenu, 0)
  const avecRecette = affiches.filter((o) => o.prevu)
  const prevu = avecRecette.reduce((t, o) => t + o.prevu, 0)
  const sorti = avecRecette.reduce((t, o) => t + o.net, 0)
  const relatif = ecartRelatif(sorti, prevu)
  const enBrouillon = periode.filter((o) => o.statut === 'brouillon')
  const bloques = enBrouillon.filter((o) => o.blocages.length).length
  return (
    <Indicateurs>
      <Kpi
        titre="Ordres affichés"
        valeur={nombre(affiches.length)}
        detail={du || au ? `du ${du ? date(du) : '…'} au ${au ? date(au) : '…'}` : 'toute la période'}
        formule={formule('ordres_affiches')}
      />
      <Kpi
        titre={brouillons ? 'À sortir' : 'Sorti net'}
        valeur={kg(net)}
        detail={
          brouillons
            ? 'rien n’a encore bougé au stock'
            : revenu
              ? `retours déduits : ${kg(revenu)} revenus`
              : 'aucun retour'
        }
        formule={formule('sorti_net')}
      />
      <Kpi
        titre="Écart à la recette"
        valeur={<EcartRecette relatif={relatif} />}
        detail={prevu ? `${kg(sorti)} sortis pour ${kg(prevu)} prévus` : 'aucun ordre selon recette'}
        ton={tonEcart(relatif)}
        formule={formule('ecart_recette')}
      />
      <Kpi
        titre="Brouillons"
        valeur={nombre(enBrouillon.length)}
        detail={bloques ? `${bloques} seraient refusés` : 'à valider'}
        ton={bloques ? 'critique' : enBrouillon.length ? 'attention' : 'ok'}
        lien="/sorties?onglet=brouillon"
        formule={formule('brouillons')}
      />
    </Indicateurs>
  )
}
