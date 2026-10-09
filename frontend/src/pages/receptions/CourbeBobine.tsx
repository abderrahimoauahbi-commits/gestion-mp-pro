/**
 * Poids de la bobine — {réf} (`/receptions?onglet=bobines&matiere=ID`, ECRANS-PRO 4.26) : la courbe
 * du poids moyen d'une bobine, réception après réception, face au poids du catalogue (pointillé),
 * et chaque mesure, la plus récente d'abord, avec sa réception et son lot.
 */
import { Courbes } from '../../composants/graphiques/Courbes'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Kpi } from '../../composants/retour/Kpi'
import { Vide } from '../../composants/retour/Vide'
import type { Colonne } from '../../composants/tableaux/colonnes'
import styles from '../plan-achat/achats.module.css'
import { DataTable } from '../../composants/tableaux/DataTable'
import { formule } from '../../lib/aide'
import { date, nombre, partSignee, VIDE } from '../../lib/format'
import { useBobines } from './donnees'
import type { EvolutionBobine, Mesure } from './types'

function colonnes(tol: number): Colonne<Mesure>[] {
  return [
    { cle: 'date', titre: 'Date', rendu: (m) => date(m.date) },
    {
      cle: 'reception',
      titre: 'Réception',
      lien: (m) => (m.reception_id ? `/receptions/${m.reception_id}` : null),
    },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    { cle: 'lot', titre: 'Lot', lien: (m) => (m.lot_id ? `/lots/${m.lot_id}` : null) },
    { cle: 'quantite_pesee', titre: 'Pesé (kg)', droite: true, rendu: (m) => nombre(m.quantite_pesee) },
    { cle: 'nb_bobines', titre: 'Bobines', droite: true, rendu: (m) => nombre(m.nb_bobines) },
    { cle: 'poids_bobine', titre: 'kg / bobine', droite: true, rendu: (m) => nombre(m.poids_bobine, 2) },
    {
      cle: 'ecart_catalogue',
      titre: 'vs catalogue',
      droite: true,
      rendu: (m) =>
        m.ecart_catalogue == null ? (
          VIDE
        ) : (
          <Badge ton={Math.abs(m.ecart_catalogue) > tol ? 'attention' : 'ok'}>
            {partSignee(m.ecart_catalogue)}
          </Badge>
        ),
    },
  ]
}

function Courbe({ b, tol }: { b: EvolutionBobine; tol: number }) {
  const mesures = [...b.historique].sort((x, y) => (x.date ?? '').localeCompare(y.date ?? ''))
  const dernier = mesures[mesures.length - 1]
  const ecartDernier = dernier?.ecart_catalogue ?? null
  return (
    <>
      <Indicateurs libelle="Indicateurs du poids de la bobine">
        <Kpi
          titre="Catalogue"
          valeur={b.poids_catalogue ? `${nombre(b.poids_catalogue, 2)} kg` : VIDE}
          formule={formule('bobines_suivies')}
          detail="poids inscrit au catalogue"
        />
        <Kpi
          titre="Dernière réception"
          valeur={`${nombre(b.dernier, 2)} kg`}
          formule={formule('bobines_hors_catalogue')}
          ton={ecartDernier != null && Math.abs(ecartDernier) > tol ? 'attention' : undefined}
          detail={`${ecartDernier == null ? VIDE : partSignee(ecartDernier)} du catalogue · ${date(b.derniere_date)}`}
        />
        <Kpi
          titre="Évolution"
          valeur={b.evolution == null ? VIDE : partSignee(b.evolution)}
          formule={formule('bobines_evolution')}
          detail={`de ${nombre(b.premier, 2)} à ${nombre(b.dernier, 2)} kg`}
        />
        <Kpi
          titre="Moyenne"
          valeur={`${nombre(b.moyenne, 2)} kg`}
          formule={formule('bobines_suivies')}
          detail={`${nombre(b.receptions)} réception(s) · ${nombre(b.mini, 2)}–${nombre(b.maxi, 2)}`}
        />
      </Indicateurs>
      <Courbes
        libelle={`Poids de la bobine — ${b.reference}`}
        etiquettes={mesures.map((m) => date(m.date))}
        series={[
          { nom: 'kg / bobine', valeurs: mesures.map((m) => m.poids_bobine), unite: 'kg' },
          ...(b.poids_catalogue
            ? [{ nom: 'catalogue', valeurs: mesures.map(() => b.poids_catalogue), unite: 'kg', trait: '4 3' }]
            : []),
        ]}
        hauteur={180}
        format={(v) => `${nombre(v, 2)} kg`}
      />
      <div className={styles.tableFenetre}>
        <DataTable<Mesure>
          libelle="Mesures du poids de la bobine"
          lignes={[...mesures].reverse()}
          colonnes={colonnes(tol)}
          cle={(m) => `${m.reception_id ?? m.reception}-${m.lot}`}
          recherche={false}
          hauteur="court"
          vide="Aucune mesure."
        />
      </div>
    </>
  )
}

export function CourbeBobine({ matiereId, onFermer }: { matiereId: number; onFermer: () => void }) {
  const lu = useBobines()
  const b = lu.data?.lignes.find((x) => x.matiere_id === matiereId)
  return (
    <Fenetre titre={`Poids de la bobine — ${b?.reference ?? ''}`} taille="large" onFermer={onFermer}>
      {!lu.data ? <Chargement quoi="le poids des bobines" /> : null}
      {lu.data && !b ? <Vide>Aucune mesure pour cette matière.</Vide> : null}
      {b ? <Courbe b={b} tol={lu.data?.tolerance ?? 0.05} /> : null}
    </Fenetre>
  )
}
