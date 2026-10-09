/**
 * Analyse › Opportunités d'économies (`/analyse?onglet=opportunites`) : où une matière comparable
 * (même composition, type, titrage ; même couleur et autre fournisseur par défaut) s'achète moins
 * cher, à la même époque, au coût rendu usine. C'est une piste à négocier, pas une décision.
 *
 * Adresse : `oq` (recherche), `couleur`, `autre`, `catalogue` (cases, `0`/`1` hors défaut),
 * `fenetre` (jours). « Effacer les filtres » remet les défauts (P8-5).
 */
import { useMemo, useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { formule } from '../../lib/aide'
import { date, kgEntier, montant, montantCourt, nombre, part, VIDE } from '../../lib/format'
import { useEtatListe } from '../catalogue/etatListe'
import styles from './analyse.module.css'
import { Case, ChoixListe, Criteres, Deux } from './briques'
import { parametresOpportunites, useOpportunites, type CriteresOpportunites } from './donnees'
import { Evolution, type MatiereComparee } from './prix/Evolution'
import type { OpportuniteLigne, Opportunites as O } from './types'

const FENETRES = [30, 45, 60, 90, 180] as const

const caracteres = (x: OpportuniteLigne) =>
  [x.composition, x.type_fil, x.titrage, x.couleur].filter((v) => v != null && v !== '').join(' · ')

const datee = (base: string, jour: string | null | undefined) =>
  jour ? `${base} du ${date(jour)}` : 'catalogue, non daté'

const PREMIERES: readonly Colonne<OpportuniteLigne>[] = [
  {
    cle: 'reference',
    titre: 'Référence · fournisseur actuel',
    recherche: (x) => [x.fournisseur_actuel, x.nature, caracteres(x)],
    rendu: (x) => (
      <Deux
        coupe
        haut={x.reference}
        titre={x.reference}
        bas={
          <>
            <strong>{x.fournisseur_actuel}</strong> · {caracteres(x)}
          </>
        }
      />
    ),
  },
  {
    cle: 'prix_actuel_mad',
    titre: 'Prix actuel (MAD / kg)',
    aide: 'Dernier coût payé pour cette matière, en MAD le kilo',
    droite: true,
    rendu: (x) => <Deux haut={nombre(x.prix_actuel_mad, 2)} bas={datee(x.base_prix, x.date_prix)} />,
  },
  {
    cle: 'reference_alternative',
    titre: 'Comparable le moins cher · chez',
    recherche: (x) => [x.fournisseur_alternatif, x.couleur_alternative],
    rendu: (x) => (
      <Deux
        coupe
        haut={x.reference_alternative || VIDE}
        titre={x.reference_alternative}
        bas={
          <>
            <strong>{x.fournisseur_alternatif}</strong>
            {x.couleur_alternative ? ` · ${x.couleur_alternative}` : ''}
          </>
        }
      />
    ),
  },
  {
    cle: 'prix_minimum_mad',
    titre: 'Son prix (MAD / kg)',
    aide: 'Le coût payé au concurrent à la date la plus proche de la nôtre',
    droite: true,
    rendu: (x) => (
      <Deux haut={nombre(x.prix_minimum_mad, 2)} bas={datee(x.base_prix_minimum, x.date_prix_minimum)} />
    ),
  },
]

function colonnes(forte: number, comparer: (x: OpportuniteLigne) => void): Colonne<OpportuniteLigne>[] {
  return [
    ...PREMIERES,
    {
      cle: 'ecart',
      titre: 'Écart',
      droite: true,
      rendu: (x) => (
        <Deux
          haut={<Badge ton={x.ecart > forte ? 'critique' : 'attention'}>{`−${part(x.ecart)}`}</Badge>}
          bas={x.ecart_jours != null ? `à ${nombre(x.ecart_jours)} j d’écart` : null}
        />
      ),
    },
    {
      cle: 'conso_annuelle',
      titre: 'Conso / an (kg)',
      droite: true,
      rendu: (x) => kgEntier(x.conso_annuelle),
    },
    {
      cle: 'economie_mad',
      titre: 'Économie / an',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (x) => <strong>{montant(x.economie_mad, 'MAD')}</strong>,
    },
    {
      cle: 'courbes',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (x) => (
        <Bouton
          taille="petit"
          titre="Les prix des deux matières dans le temps, sur une même courbe"
          onClick={() => comparer(x)}
        >
          Courbes
        </Bouton>
      ),
    },
  ]
}

function IndicateursOpportunites({ o }: { o: O }) {
  const forte = o.seuils.forte ?? 0.05
  const meilleure = o.lignes[0]
  const sansDate = o.ecartees.sans_date ?? 0
  const horsFenetre = o.ecartees.hors_fenetre ?? 0
  return (
    <Indicateurs libelle="Indicateurs des opportunités">
      <Kpi
        titre="Économie possible"
        valeur={montantCourt(o.total_mad, 'MAD')}
        exact={montant(o.total_mad, 'MAD')}
        ton={o.total_mad > 0 ? 'attention' : 'ok'}
        detail="par an, au rythme de consommation actuel"
        formule={formule('opportunite')}
      />
      <Kpi
        titre="Opportunités"
        valeur={nombre(o.lignes.length)}
        detail={`dont ${nombre(o.lignes.filter((x) => x.ecart > forte).length)} à plus de ${part(forte, 0)} d’écart`}
        formule={formule('opportunites_nombre')}
      />
      <Kpi
        titre="La plus forte"
        valeur={meilleure ? montantCourt(meilleure.economie_mad, 'MAD') : VIDE}
        detail={meilleure ? meilleure.reference : 'aucune'}
        formule={formule('opportunites_plus_forte')}
      />
      <Kpi
        titre="Écartées"
        valeur={nombre(sansDate + horsFenetre)}
        detail={`${nombre(sansDate)} sans date · ${nombre(horsFenetre)} à plus de ${nombre(o.fenetre_jours)} j d’écart`}
        formule={formule('opportunites_ecartees')}
      />
    </Indicateurs>
  )
}

/** La méthode, sur une ligne (le texte entier en infobulle). */
function methodeDe(o: O): string {
  const rendus = o.lignes.filter((x) => x.base_prix === 'coût rendu' || x.base_prix_minimum === 'coût rendu')
  const avant = rendus.length
    ? `${nombre(rendus.length)} opportunité(s) reposent sur au moins un coût rendu usine. `
    : ''
  return `${avant}${o.avertissement}`
}

/** Les critères lus dans l'adresse (absents : les défauts). */
function lireCriteres(lire: (cle: string) => string): CriteresOpportunites {
  const fenetre = Number(lire('fenetre'))
  return {
    meme_couleur: lire('couleur') !== '0',
    autre_fournisseur: lire('autre') !== '0',
    prix_catalogue: lire('catalogue') === '1',
    fenetre_jours: fenetre > 0 ? fenetre : null,
  }
}

interface OutilsProps {
  criteres: CriteresOpportunites
  poser: (cle: string, v: string | null) => void
  fenetre: number
  occupe: boolean
  criteresPoses: number
  onEffacer: () => void
}

/** « Comparé à : » trois cases, la fenêtre de jours, « Effacer les filtres » (remet les défauts). */
function OutilsOpportunites({ criteres, poser, fenetre, occupe, criteresPoses, onEffacer }: OutilsProps) {
  return (
    <>
      <span
        className={styles.note}
        title="Une matière de même composition, même type et même titrage ; et, selon les cases :"
      >
        Comparé à :
      </span>
      <Case
        valeur={criteres.meme_couleur}
        titre="De la même couleur que la nôtre"
        onChange={(v) => poser('couleur', v ? null : '0')}
      >
        même couleur
      </Case>
      <Case
        valeur={criteres.autre_fournisseur}
        titre="Chez un autre fournisseur que le nôtre"
        onChange={(v) => poser('autre', v ? null : '0')}
      >
        autre fournisseur
      </Case>
      <Case
        valeur={criteres.prix_catalogue}
        titre="Y compris les prix de catalogue, non datés : on ne sait pas s’ils sont d’avant ou d’après une hausse"
        onChange={(v) => poser('catalogue', v ? '1' : null)}
      >
        prix de catalogue aussi
      </Case>
      <ChoixListe
        libelle="Écart maximal entre les deux prix"
        titre="L’écart maximal entre les dates des deux prix comparés : plus il est court, plus la comparaison est juste quand les prix bougent"
        valeur={criteres.fenetre_jours ? String(criteres.fenetre_jours) : ''}
        options={[
          { valeur: '', libelle: `à ${nombre(fenetre)} j au plus (réglage)` },
          ...FENETRES.map((j) => ({ valeur: String(j), libelle: `à ${j} j au plus` })),
        ]}
        onChange={(v) => poser('fenetre', v || null)}
      />
      {occupe ? <span className={styles.note}>mise à jour…</span> : null}
      <Criteres nombre={criteresPoses} onEffacer={onEffacer} />
    </>
  )
}

export function Opportunites() {
  const etat = useEtatListe('oq', ['couleur', 'autre', 'catalogue', 'fenetre'])
  const criteres = lireCriteres(etat.lire)
  const lu = useOpportunites(criteres)
  const [aComparer, setAComparer] = useState<MatiereComparee[] | null>(null)
  const forte = lu.data?.seuils.forte ?? 0.05
  const cols = useMemo(
    () =>
      colonnes(forte, (x) =>
        setAComparer([
          { reference: x.reference, matiere_id: x.matiere_id ?? null },
          { reference: x.reference_alternative, matiere_id: x.matiere_alternative_id ?? null },
        ]),
      ),
    [forte],
  )
  if (lu.isPending) return <Chargement quoi="les opportunités d’économies" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const o = lu.data
  const poser = (cle: string, v: string | null) => etat.choix.poser(cle, v)
  const n = Object.keys(etat.choix.valeurs).length + (etat.recherche.valeur.trim() ? 1 : 0)
  const methode = methodeDe(o)
  return (
    <>
      <IndicateursOpportunites o={o} />
      <Carte
        titre={`Opportunités d’économies — ${nombre(o.lignes.length)} trouvée(s)`}
        serre
        remplir
        className={styles.carteListe}
      >
        <Note uneLigne={methode}>{methode}</Note>
        <DataTable<OpportuniteLigne>
          libelle="Opportunités d’économies"
          lignes={o.lignes}
          colonnes={cols}
          cle={(x) => `${x.reference}|${x.reference_alternative}|${x.fournisseur_actuel}`}
          recherche={etat.recherche}
          placeholder="Matière, fournisseur, couleur… plusieurs mots"
          triInitial={{ cle: 'economie_mad', sens: -1 }}
          vide="Aucune matière comparable ne s’achète moins cher avec ces critères."
          exporter={{ route: '/export/opportunites', parametres: parametresOpportunites(criteres) }}
          outils={
            <OutilsOpportunites
              criteres={criteres}
              poser={poser}
              fenetre={o.fenetre_jours}
              occupe={lu.isFetching}
              criteresPoses={n}
              onEffacer={etat.choix.effacer}
            />
          }
        />
      </Carte>
      {aComparer ? <Evolution matieres={aComparer} onFermer={() => setAComparer(null)} /> : null}
    </>
  )
}
