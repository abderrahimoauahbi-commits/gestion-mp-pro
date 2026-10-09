/**
 * Réceptions › Poids des bobines (ECRANS-PRO 4.25) : poids pesé ÷ bobines comptées, à chaque
 * réception validée, par matière ; la tolérance est celle du réglage (jamais écrite en dur). Une
 * ligne ouvre la courbe de la matière (`?matiere=ID`).
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Bouton } from '../../composants/saisie/Bouton'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import { formule } from '../../lib/aide'
import { date, nombre, part, partSignee, VIDE } from '../../lib/format'
import type { Role } from '../../lib/types'
import styles from '../plan-achat/achats.module.css'
import { deux } from '../plan-achat/colonnesFournisseurs'
import { adresseMatiere, lienSi } from '../plan-achat/liens'
import { useBobines } from './donnees'
import type { EvolutionBobine, EvolutionBobines } from './types'

/** Une matière à écart : son dernier poids hors catalogue, ou une évolution au-delà de la tolérance. */
export const aEcart = (b: EvolutionBobine, tol: number) =>
  b.hors_tolerance || Math.abs(b.evolution ?? 0) > tol

function colonnes1(
  tol: number,
  role: Role,
  _courbe: (b: EvolutionBobine) => void,
): Colonne<EvolutionBobine>[] {
  return [
    {
      cle: 'reference',
      titre: 'Référence',
      lien: (b) => (b.matiere_id ? lienSi(role, adresseMatiere(b.matiere_id)) : null),
    },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    {
      cle: 'poids_catalogue',
      titre: 'Catalogue kg / bobine',
      droite: true,
      rendu: (b) => (b.poids_catalogue ? nombre(b.poids_catalogue, 2) : VIDE),
    },
    { cle: 'premier', titre: 'Premier', droite: true, rendu: (b) => nombre(b.premier, 2) },
    {
      cle: 'dernier',
      titre: 'Dernier',
      droite: true,
      rendu: (b) =>
        deux(<strong>{nombre(b.dernier, 2)}</strong>, b.derniere_date ? `le ${date(b.derniere_date)}` : null),
    },
    {
      cle: 'evolution',
      titre: 'Évolution',
      droite: true,
      rendu: (b) =>
        b.evolution == null ? (
          VIDE
        ) : (
          <Badge
            ton={Math.abs(b.evolution) < 0.005 ? 'neutre' : Math.abs(b.evolution) > tol ? 'attention' : 'ok'}
          >
            {partSignee(b.evolution)}
          </Badge>
        ),
    },
  ]
}

function colonnes2(
  _tol: number,
  _role: Role,
  courbe: (b: EvolutionBobine) => void,
): Colonne<EvolutionBobine>[] {
  return [
    {
      cle: 'ecart_catalogue',
      titre: 'vs catalogue',
      droite: true,
      rendu: (b) =>
        b.ecart_catalogue == null ? (
          VIDE
        ) : (
          <Badge ton={b.hors_tolerance ? 'critique' : 'ok'}>{partSignee(b.ecart_catalogue)}</Badge>
        ),
    },
    {
      cle: 'mini',
      titre: 'Mini – maxi',
      droite: true,
      rendu: (b) => `${nombre(b.mini, 2)} – ${nombre(b.maxi, 2)}`,
    },
    { cle: 'receptions', titre: 'Réceptions', droite: true },
    {
      cle: 'courbe',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (b) => (
        <span onClick={(e) => e.stopPropagation()}>
          <Bouton taille="petit" titre="La courbe du poids et chaque réception" onClick={() => courbe(b)}>
            Courbe
          </Bouton>
        </span>
      ),
    },
  ]
}

function colonnes(tol: number, role: Role, courbe: (b: EvolutionBobine) => void): Colonne<EvolutionBobine>[] {
  return [...colonnes1(tol, role, courbe), ...colonnes2(tol, role, courbe)]
}

function IndicateursBobines({ d }: { d: EvolutionBobines }) {
  const tol = d.tolerance
  return (
    <Indicateurs libelle="Indicateurs du poids des bobines">
      <Kpi
        titre="Matières suivies"
        valeur={nombre(d.lignes.length)}
        formule={formule('bobines_suivies')}
        detail="bobines pesées et comptées"
      />
      <Kpi
        titre="Hors catalogue"
        valeur={nombre(d.hors_tolerance)}
        formule={formule('bobines_hors_catalogue')}
        ton={d.hors_tolerance ? 'attention' : 'ok'}
        detail={`dernière pesée à ±${part(tol, 0)} et plus`}
        lien="/receptions?onglet=bobines&ecarts=1"
      />
      <Kpi
        titre="Bobines qui s’alourdissent"
        valeur={nombre(d.alourdies)}
        formule={formule('bobines_evolution')}
        detail={`hausse de plus de ${part(tol, 0)} depuis la 1re réception`}
      />
      <Kpi
        titre="Bobines qui s’allègent"
        valeur={nombre(d.allegees)}
        formule={formule('bobines_evolution')}
        detail={`baisse de plus de ${part(tol, 0)} depuis la 1re réception`}
      />
    </Indicateurs>
  )
}

export function OngletBobines({
  etat,
  role,
  ecarts,
  onEcarts,
  onCourbe,
}: {
  etat: EtatTable
  role: Role
  ecarts: boolean
  onEcarts: (v: boolean) => void
  onCourbe: (matiereId: number) => void
}) {
  const lu = useBobines()
  const tol = lu.data?.tolerance ?? 0.05
  const lignes = useMemo(
    () => (lu.data?.lignes ?? []).filter((b) => !ecarts || aEcart(b, tol)),
    [lu.data, ecarts, tol],
  )
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  if (!lu.data) return <Chargement quoi="le poids des bobines" />
  const d = lu.data
  const courbe = (b: EvolutionBobine) => b.matiere_id && onCourbe(b.matiere_id)
  return (
    <>
      <IndicateursBobines d={d} />
      <Carte
        titre={
          <span title="Poids pesé ÷ bobines comptées, à chaque réception validée. Un clic sur une ligne montre sa courbe.">
            Par matière
          </span>
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <DataTable<EvolutionBobine>
          libelle="Poids des bobines par matière"
          lignes={lignes}
          colonnes={colonnes(tol, role, courbe)}
          filtres={[{ cle: 'fournisseur_nom', libelle: 'Fournisseur', valeur: (b) => b.fournisseur }]}
          cle={(b) => `${b.matiere_id ?? b.reference}-${b.fournisseur}`}
          recherche={etat.recherche}
          choix={etat.choix}
          placeholder="Référence, fournisseur…"
          cliquable={courbe}
          outils={<Interrupteur valeur={ecarts} onChange={onEcarts} libelle="Écarts seulement" />}
          exporter={{ route: '/export/receptions/bobines', parametres: { ecarts: ecarts || undefined } }}
          vide={
            d.lignes.length
              ? 'Aucune matière ne correspond.'
              : 'Dès qu’une réception validée porte un nombre de bobines, le poids moyen de la bobine s’inscrit ici et se suit dans le temps.'
          }
        />
      </Carte>
    </>
  )
}
