/**
 * Analyse › Valorisation (`/analyse?onglet=valorisation`) : ce que vaut le stock détenu —
 * magasins et métiers — au coût moyen pondéré des achats réels (à défaut d'achat, au prix du
 * catalogue), à une date choisie : le journal rejoué jusqu'au soir de ce jour-là, le fil monté ce
 * soir-là compris (décision U8, lot D8). Le total est celui du Cockpit (E-06).
 *
 * Adresse : `vq` (recherche), `au` (date), `tout` (matières sans stock). L'écart avec le catalogue
 * est signalé au-delà d'un seuil fixe de 2 %, écrit dans la formule (P8-4).
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { DateChamp } from '../../composants/saisie/DateChamp'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { formule } from '../../lib/aide'
import {
  date,
  kg,
  metres,
  montant,
  montantCourt,
  mois,
  nombre,
  part,
  prixUnite,
  VIDE,
} from '../../lib/format'
import { ajouterJours, aujourdhui } from '../../lib/heure'
import { useEtatListe } from '../catalogue/etatListe'
import styles from './analyse.module.css'
import { ChoixListe, Case, Criteres } from './briques'
import { useValorisation } from './donnees'
import type { LigneValorisation, Valorisation as V } from './types'

/** Le seuil fixe de l'écart avec le catalogue (part de la valeur du stock), dit dans la formule. */
export const SEUIL_ECART_CATALOGUE = 0.02

/** Le dernier jour des douze mois écoulés, du plus récent au plus ancien (« AAAA-MM-JJ »). */
export function finsDeMois(jour: string): string[] {
  const fins: string[] = []
  let debut = `${jour.slice(0, 7)}-01`
  for (let i = 0; i < 12; i += 1) {
    const fin = ajouterJours(debut, -1)
    fins.push(fin)
    debut = `${fin.slice(0, 7)}-01`
  }
  return fins
}

const COLONNES: readonly Colonne<LigneValorisation>[] = [
  {
    cle: 'reference',
    titre: 'Référence',
    recherche: (x) => [x.nature, x.designation, x.devise],
    rendu: (x) => (
      <>
        <span className={styles.ref} title={x.reference}>
          {x.reference}
        </span>
        <span className={styles.dessous}>{x.nature}</span>
      </>
    ),
  },
  { cle: 'fournisseur', titre: 'Fournisseur' },
  {
    cle: 'stock_magasin',
    titre: 'Magasins',
    aide: 'En kg, quarantaine comprise ; le cuir, les franges et le ruban compris',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (x) => kg(x.stock_magasin),
  },
  {
    cle: 'stock_machine',
    titre: 'Sur les métiers',
    aide: 'Le fil monté, pas encore tissé : compris dans le stock détenu et sa valeur',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (x) => (x.stock_machine ? kg(x.stock_machine) : VIDE),
  },
  {
    cle: 'stock',
    titre: 'Stock détenu',
    aide: 'Magasins + sur les métiers',
    droite: true,
    unite: 'kg',
    total: true,
    rendu: (x) => (
      <>
        <strong>{kg(x.stock)}</strong>
        {x.kg_par_ml && x.stock ? (
          <span className={styles.dessous}>{metres(x.stock, x.kg_par_ml)}</span>
        ) : null}
      </>
    ),
  },
  {
    cle: 'cmup_mad',
    titre: 'Coût moyen (MAD)',
    aide: 'Coût moyen pondéré des achats réels, recalculé à chaque entrée ; à défaut d’achat, prix du catalogue — au kilo',
    droite: true,
    rendu: (x) => `${prixUnite(x.cmup_mad, 'MAD', 'kg')}`,
  },
  {
    cle: 'prix_catalogue',
    titre: 'Prix catalogue',
    droite: true,
    rendu: (x) => prixUnite(x.prix_catalogue, x.devise, 'kg'),
  },
  {
    cle: 'valeur_mad',
    titre: 'Valeur (MAD)',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (x) => <strong>{nombre(x.valeur_mad)}</strong>,
  },
  {
    cle: 'ecart_mad',
    titre: 'Écart catalogue',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (x) => (Math.abs(x.ecart_mad) >= 0.5 ? nombre(x.ecart_mad) : VIDE),
  },
]

function IndicateursValorisation({ v }: { v: V }) {
  const signale = Math.abs(v.ecart_mad) > SEUIL_ECART_CATALOGUE * Math.max(v.total_mad, 1)
  return (
    <Indicateurs libelle="Indicateurs de la valorisation">
      <Kpi
        titre="Valeur du stock détenu"
        valeur={montantCourt(v.total_mad, 'MAD')}
        exact={`${montant(v.total_mad, 'MAD')} au ${date(v.date_reference)}`}
        detail={kg(v.total_kg)}
        formule={formule('valeur_stock')}
      />
      <Kpi
        titre="Dans les magasins"
        valeur={montantCourt(v.total_magasin_mad, 'MAD')}
        exact={montant(v.total_magasin_mad, 'MAD')}
        detail={kg(v.total_kg_magasin)}
        formule={formule('valorisation_magasins')}
      />
      <Kpi
        titre="Sur les métiers"
        valeur={montantCourt(v.total_machine_mad, 'MAD')}
        exact={montant(v.total_machine_mad, 'MAD')}
        detail={`${kg(v.total_kg_machine)} montés, compris dans le stock`}
        formule={formule('sur_les_metiers')}
      />
      <Kpi
        titre="Matières en stock"
        valeur={`${nombre(v.nb_en_stock)} sur ${nombre(v.nb_matieres)}`}
        detail="avec stock ou fil monté"
        formule={formule('valorisation_matieres')}
      />
      <Kpi
        titre="Écart avec le catalogue"
        valeur={montantCourt(v.ecart_mad, 'MAD')}
        exact={montant(v.ecart_mad, 'MAD')}
        detail={`coût payé − catalogue · signalé au-delà de ${part(SEUIL_ECART_CATALOGUE, 0)}`}
        ton={signale ? 'attention' : undefined}
        formule={formule('valorisation_ecart')}
      />
    </Indicateurs>
  )
}

/** « Au » : aujourd'hui, une des douze fins de mois, ou une autre date (au plus aujourd'hui). */
function ChoixDate({ au, onChange }: { au: string; onChange: (v: string | null) => void }) {
  const jour = aujourdhui()
  const fins = finsDeMois(jour)
  const autre = au !== '' && !fins.includes(au)
  const options = [
    { valeur: '', libelle: 'Au : aujourd’hui' },
    ...fins.map((f) => ({ valeur: f, libelle: `Au : fin ${mois(f)} (${date(f)})` })),
    { valeur: 'autre', libelle: 'Au : autre date…' },
  ]
  return (
    <>
      <ChoixListe
        libelle="Au"
        titre="La valeur au soir de ce jour : le journal rejoué jusque-là"
        valeur={autre ? 'autre' : au}
        options={options}
        onChange={(v) => onChange(v === 'autre' ? ajouterJours(jour, -1) : v || null)}
      />
      {autre ? (
        <DateChamp
          libelle="Date de la valorisation"
          valeur={au}
          max={jour}
          onChange={(v) => onChange(v || null)}
        />
      ) : null}
    </>
  )
}

export function Valorisation() {
  const etat = useEtatListe('vq', ['au', 'tout'])
  const au = etat.lire('au')
  const tout = etat.lire('tout') === '1'
  const lu = useValorisation(au)
  const lignes = useMemo(
    () => (lu.data?.lignes ?? []).filter((x) => tout || Math.abs(x.stock) > 1e-6),
    [lu.data, tout],
  )
  const total = lignes.reduce((s, x) => s + x.valeur_mad, 0)
  const criteres = (etat.recherche.valeur.trim() ? 1 : 0) + (au ? 1 : 0) + (tout ? 1 : 0)
  if (lu.isPending) return <Chargement quoi="la valorisation" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const v = lu.data
  return (
    <>
      <IndicateursValorisation v={v} />
      <Carte
        titre={`Valeur par matière, la plus lourde d’abord — ${nombre(lignes.length)} matière(s), ${montant(total, 'MAD')}`}
        serre
        remplir
        className={styles.carteListe}
      >
        {au && au < aujourdhui() ? (
          <Note
            uneLigne={`Au ${date(au)} au soir : le stock et le coût moyen rejoués sur le journal jusqu’à ce jour-là, le fil monté sur les métiers ce soir-là compris.`}
          >
            Au {date(au)} au soir : le stock et le coût moyen rejoués sur le journal jusqu’à ce jour-là, le
            fil monté sur les métiers ce soir-là compris.
          </Note>
        ) : null}
        <DataTable<LigneValorisation>
          libelle="Valorisation par matière"
          lignes={lignes}
          colonnes={COLONNES}
          cle={(x) => `${x.reference}|${x.fournisseur}`}
          recherche={etat.recherche}
          placeholder="Référence, fournisseur, devise… plusieurs mots"
          triInitial={{ cle: 'valeur_mad', sens: -1 }}
          vide="Aucun stock à valoriser."
          exporter={{ route: '/export/valorisation', parametres: { date: au || undefined } }}
          outils={
            <>
              <ChoixDate au={au} onChange={(x) => etat.choix.poser('au', x)} />
              <Case valeur={tout} onChange={(x) => etat.choix.poser('tout', x ? '1' : null)}>
                montrer aussi les matières sans stock
              </Case>
              <Criteres nombre={criteres} onEffacer={etat.choix.effacer} />
            </>
          }
        />
      </Carte>
    </>
  )
}
