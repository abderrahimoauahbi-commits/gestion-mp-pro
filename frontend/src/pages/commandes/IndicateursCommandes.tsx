/**
 * Les indicateurs des commandes (ECRANS-PRO 4.5), comptés par le serveur sur **tous** les bons
 * ouverts, quels que soient l'onglet, la recherche et les filtres (la rangée le dit) ; chacun mène
 * à ce qu'il compte. L'écran ne recompte rien : les nombres viennent de `/commandes/apercu`.
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { montant, montantCourt, nombre } from '../../lib/format'
import type { Role } from '../../lib/types'
import type { IndicateursServeur } from './types'

/** Les deux premiers : ce qui est ouvert, et ce qui est engagé chez les fournisseurs. */
function Ouverts({ i, direction }: { i: IndicateursServeur; direction: boolean }) {
  return (
    <>
      <Kpi
        titre="Bons ouverts"
        valeur={nombre(i.ouverts)}
        formule={formule('commandes_ouvertes')}
        ton={direction && i.a_approuver ? 'urgent' : undefined}
        detail={
          <span
            title={
              i.a_approuver
                ? direction
                  ? 'Votre accord est attendu'
                  : 'En attente de la direction'
                : undefined
            }
          >
            {nombre(i.brouillons)} brouillon(s) · {nombre(i.a_approuver)} à approuver
          </span>
        }
        lien="/commandes?onglet=a_approuver"
      />
      <Kpi
        titre="Montant engagé"
        valeur={montantCourt(i.engage, 'MAD')}
        exact={montant(i.engage, 'MAD')}
        formule={formule('commandes_engage')}
        detail={
          <span
            title={
              i.partis_estimes
                ? `dont ${nombre(i.partis_estimes)} bon(s) estimé(s) au prix du catalogue, prix à confirmer`
                : undefined
            }
          >
            {nombre(i.partis)} bon(s) partis
          </span>
        }
      />
      <Kpi
        titre="Reste à livrer (MAD)"
        valeur={montantCourt(i.reste, 'MAD')}
        exact={montant(i.reste, 'MAD')}
        formule={formule('commandes_reste')}
        detail="pas encore arrivé"
      />
    </>
  )
}

export function IndicateursCommandes({ i, role }: { i: IndicateursServeur; role: Role }) {
  return (
    <Indicateurs libelle="Indicateurs des commandes (tous les bons)">
      <Ouverts i={i} direction={role === 'direction'} />
      <Kpi
        titre="Prix à confirmer"
        valeur={nombre(i.a_confirmer)}
        formule={formule('commandes_prix_a_confirmer')}
        ton={i.a_confirmer ? 'attention' : 'ok'}
        detail="bons partis"
        lien="/commandes?onglet=envoyee"
      />
      <Kpi
        titre="En retard"
        valeur={nombre(i.retard)}
        formule={formule('commandes_retard')}
        ton={i.retard ? 'critique' : 'ok'}
        detail="date prévue dépassée"
        lien="/commandes?filtre=retard"
      />
    </Indicateurs>
  )
}
