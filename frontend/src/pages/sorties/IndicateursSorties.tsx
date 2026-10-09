/**
 * Les indicateurs des Sorties, sur les ordres affichés : leur nombre (total du serveur), le sorti
 * net (ou « À sortir » sur les brouillons), l'écart à la recette (un manque critique, un excès à
 * surveiller, P2-25), et les brouillons de la période (cliquable). Les sommes viennent de l'aperçu
 * du serveur (`/ordres/apercu`) : mêmes chiffres qu'avant, mais sans charger toute la liste.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { date, kg, nombre } from '../../lib/format'
import { EcartRecette, ecartRelatif, tonEcart } from './ecart'

export interface IndicateursProps {
  /** Le nombre d'ordres affichés (total du serveur pour le filtre). */
  total: number
  /** Σ sorti net (ou Σ à sortir sur les brouillons). */
  net: number
  /** Σ revenu (retours). */
  revenu: number
  /** Σ prévu des ordres selon recette. */
  prevu: number
  /** Σ sorti net des ordres selon recette. */
  sorti: number
  /** Brouillons de la période, et combien seraient refusés. */
  brouillonsPeriode: number
  brouillonsBloques: number
  brouillons: boolean
  du?: string
  au?: string
}

export function IndicateursSorties({
  total,
  net,
  revenu,
  prevu,
  sorti,
  brouillonsPeriode,
  brouillonsBloques,
  brouillons,
  du,
  au,
}: IndicateursProps) {
  const relatif = ecartRelatif(sorti, prevu)
  return (
    <Indicateurs>
      <Kpi
        titre="Ordres affichés"
        valeur={nombre(total)}
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
        valeur={nombre(brouillonsPeriode)}
        detail={brouillonsBloques ? `${brouillonsBloques} seraient refusés` : 'à valider'}
        ton={brouillonsBloques ? 'critique' : brouillonsPeriode ? 'attention' : 'ok'}
        lien="/sorties?onglet=brouillon"
        formule={formule('brouillons')}
      />
    </Indicateurs>
  )
}
