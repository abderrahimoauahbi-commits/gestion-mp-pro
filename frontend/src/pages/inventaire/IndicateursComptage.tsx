/**
 * Les indicateurs de la fenêtre de comptage (ECRANS-PRO partie 6) : lots figés, comptés, hors
 * tolérance, à recompter, écart total, valeur de l'écart (qui voit les prix), recomptages à
 * quatre yeux. Chacun porte sa formule (`aide.json`).
 */
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { formule } from '../../lib/aide'
import { montant, nombre, nombreSigne, part } from '../../lib/format'
import type { Totaux } from './calculComptage'
import { tonHorsTolerance } from './types'

export function IndicateursComptage({ t, voitPrix }: { t: Totaux; voitPrix: boolean }) {
  return (
    <Indicateurs libelle="Indicateurs du comptage">
      <Kpi titre="Lots figés" valeur={nombre(t.lignes)} formule={formule('inventaire_lots_figes')} />
      <Kpi
        titre="Comptés"
        valeur={`${nombre(t.comptees)} / ${nombre(t.lignes)}`}
        detail={`${part(t.lignes ? t.comptees / t.lignes : 0, 0)} du comptage`}
        ton={t.lignes && t.comptees === t.lignes ? 'ok' : undefined}
        formule={formule('inventaire_comptes')}
      />
      <Kpi
        titre="Hors tolérance"
        valeur={nombre(t.hors)}
        detail={t.sansJustification ? `${nombre(t.sansJustification)} sans justification` : 'tous justifiés'}
        ton={t.sansJustification ? 'rupture' : tonHorsTolerance(t.hors, 0)}
        formule={formule('inventaire_hors_tolerance')}
      />
      <Kpi
        titre="À recompter"
        valeur={nombre(t.aRecompter)}
        detail={`${nombre(t.recomptees)} recompté(s) · le recomptage ajuste`}
        ton={t.aRecompter ? 'attention' : undefined}
        formule={formule('inventaire_a_recompter')}
      />
      <Kpi
        titre="Écart total"
        valeur={nombreSigne(t.ecart, 1)}
        unite="kg"
        detail="retenu − théorique, lots comptés"
        formule={formule('inventaire_ecart')}
      />
      {voitPrix ? (
        <Kpi
          titre="Valeur de l’écart"
          valeur={nombreSigne(t.valeur, 0)}
          unite="MAD"
          detail={`${montant(t.valeurAbsolue, 'MAD')} sans signe`}
          formule={formule('inventaire_valeur_ecart')}
        />
      ) : null}
      <Kpi
        titre="Recomptages à quatre yeux"
        valeur={nombre(t.memePersonne)}
        detail={`${nombre(t.memePersonne)} par la même personne`}
        ton={t.memePersonne ? 'attention' : undefined}
        formule={formule('inventaire_quatre_yeux')}
      />
    </Indicateurs>
  )
}
