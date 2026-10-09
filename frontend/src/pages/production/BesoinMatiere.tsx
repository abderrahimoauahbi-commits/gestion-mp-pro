/**
 * Besoin d'une matière (`/production/besoins/:matiereId`, fenêtre sur l'onglet « Besoins matière ») :
 * d'où vient le besoin — les qualités au plan qui la tirent, leurs kg/m² et leurs kilos mois par
 * mois. L'addition affichée tombe juste : chaque mois, les qualités s'additionnent exactement au
 * besoin du plan écrit dessous (`repartir`), et chaque ligne à son total.
 */
import { Link, useNavigate } from 'react-router'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { Cadre } from '../../composants/tableaux/Cadre'
import { formule } from '../../lib/aide'
import { jours, kg, kgEtMetres, metres, moisCourt, nombre, partSignee, VIDE } from '../../lib/format'
import { statut, cleStock } from '../../lib/statuts'
import { tableauJuste } from '../stock/addition'
import stock from '../stock/stock.module.css'
import { somme, type BesoinMatiere as Besoin, type BesoinsDetailles } from './plan'

function IndicateursBesoin({ b, voitAchats }: { b: Besoin; voitAchats: boolean }) {
  const coef = b.coefficient_realisation
  const ton = b.statut ? statut('stock', cleStock(b.statut)).ton : undefined
  return (
    <Indicateurs libelle="Indicateurs du besoin">
      <Kpi
        titre="Besoin du plan"
        valeur={kg(b.total)}
        detail={`douze mois, perte comprise${b.kg_par_ml ? ` · ${metres(b.total, b.kg_par_ml)}` : ''}`}
        formule={formule('besoin_mois')}
      />
      <Kpi
        titre="Retenu par le plan d’achat"
        valeur={kg(b.total_retenu)}
        detail={
          coef != null
            ? `corrigé par le réel : × ${nombre(coef, 2)} (${partSignee(coef - 1, 0)})`
            : b.conso_reelle != null && !b.total
              ? 'hors plan : la consommation réelle prolongée'
              : 'pas encore de consommation pour corriger le plan'
        }
        ton={coef != null && Math.abs(coef - 1) > 0.15 ? 'attention' : undefined}
        formule={formule('besoin_retenu')}
      />
      <Kpi
        titre="Disponible"
        valeur={kgEtMetres(b.stock_disponible, b.kg_par_ml)}
        detail={`${kg(b.bc_en_cours)} en commande · couverture ${b.couverture_jours == null ? VIDE : jours(b.couverture_jours)}`}
        formule={formule('stock_detenu')}
      />
      {voitAchats ? (
        <Kpi
          titre="À commander"
          valeur={
            b.quantite_a_commander == null
              ? VIDE
              : b.quantite_a_commander > 0
                ? kg(b.quantite_a_commander)
                : 'rien'
          }
          detail={
            b.kg_par_ml && (b.quantite_a_commander ?? 0) > 0
              ? `${metres(b.quantite_a_commander, b.kg_par_ml)}, à titre indicatif`
              : b.statut
                ? statut('stock', cleStock(b.statut)).libelle
                : undefined
          }
          ton={ton}
          formule={formule('quantite_a_commander')}
        />
      ) : null}
    </Indicateurs>
  )
}

function TeteBesoin({ mois }: { mois: readonly string[] }) {
  return (
    <thead>
      <tr>
        <th className={stock.fige}>Qualité</th>
        <th className={stock.droite} title="Cette matière par m² de la qualité, perte comprise">
          kg/m²
        </th>
        {mois.map((m) => (
          <th key={m} className={stock.droite}>
            {moisCourt(m)}
          </th>
        ))}
        <th className={stock.droite}>Total (kg)</th>
      </tr>
    </thead>
  )
}

function TableBesoin({ b, mois }: { b: Besoin; mois: readonly string[] }) {
  if (!b.qualites.length) return <Vide>Aucune qualité au plan n’utilise cette matière.</Vide>
  const { lignes, totaux } = tableauJuste(
    b.qualites.map((q) => q.kg),
    b.kg,
  )
  return (
    <Cadre hauteur="fenetre">
      <table className={stock.tableSimple} aria-label="D’où vient le besoin">
        <TeteBesoin mois={mois} />
        <tbody>
          {b.qualites.map((q, r) => (
            <tr key={q.qualite}>
              <td className={stock.fige}>
                {q.qualite_id ? (
                  <Link to={`/qualites/${q.qualite_id}?onglet=recette`}>{q.qualite}</Link>
                ) : (
                  q.qualite
                )}
              </td>
              <td className={stock.droite}>{nombre(q.kg_m2, 3)}</td>
              {(lignes[r] ?? []).map((v, i) => (
                <td key={i} className={stock.droite}>
                  {v ? nombre(v) : VIDE}
                </td>
              ))}
              <td className={stock.droite}>
                <strong>{nombre(somme(lignes[r] ?? []))}</strong>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td className={stock.fige}>Besoin du plan</td>
            <td />
            {totaux.map((v, i) => (
              <td key={i} className={stock.droite}>
                {nombre(v)}
              </td>
            ))}
            <td className={stock.droite}>{nombre(somme(totaux))}</td>
          </tr>
          {Math.abs(b.total_retenu - b.total) > 0.5 ? (
            <tr>
              <td className={stock.fige}>Retenu (achats)</td>
              <td />
              {b.retenu.map((v, i) => (
                <td key={i} className={stock.droite}>
                  {nombre(v)}
                </td>
              ))}
              <td className={stock.droite}>{nombre(b.total_retenu)}</td>
            </tr>
          ) : null}
        </tfoot>
      </table>
    </Cadre>
  )
}

export function BesoinMatiere({
  id,
  besoins,
  voitAchats,
  onFermer,
}: {
  id: number
  besoins: BesoinsDetailles
  voitAchats: boolean
  onFermer: () => void
}) {
  const navigate = useNavigate()
  const b = besoins.lignes.find((x) => x.matiere_id === id)
  const pied = (
    <>
      <Bouton onClick={() => navigate(`/stock/matieres/${id}`)}>Fiche matière</Bouton>
      <span className={stock.pousse} />
      {voitAchats && b ? (
        <Bouton
          variante="principal"
          onClick={() => navigate(`/plan-achat?onglet=references&q=${encodeURIComponent(b.reference)}`)}
        >
          Ouvrir le plan d’achat →
        </Bouton>
      ) : null}
    </>
  )
  return (
    <Fenetre
      titre={b ? `${b.reference} — d’où vient le besoin` : 'Besoin d’une matière'}
      sous={b ? [b.role, b.nature, b.designation, b.fournisseur].filter(Boolean).join(' · ') : undefined}
      taille="tresLarge"
      onFermer={onFermer}
      pied={pied}
    >
      {b ? (
        <>
          <IndicateursBesoin b={b} voitAchats={voitAchats} />
          <TableBesoin b={b} mois={besoins.mois} />
        </>
      ) : (
        <Vide>Cette matière n’a aucun besoin au plan.</Vide>
      )}
    </Fenetre>
  )
}
