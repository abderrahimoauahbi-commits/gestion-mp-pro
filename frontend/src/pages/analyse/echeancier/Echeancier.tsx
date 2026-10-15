/**
 * Analyse › Échéancier (`/analyse?onglet=echeancier`) : ce qu'il faudra payer, et quand —
 * factures des fournisseurs et frais d'importation. **Tous** les filtres partent au serveur
 * (recherche, nature, du, au) et les indicateurs les suivent ; « Par mois » a son total (P8-21).
 * Quatre vues : Échéances, Par mois, À dater, Réglées (`evue`). Adresse : `eq`, `nature`, `du`, `au`.
 * L'échu reste compté quelle que soit la période (A-21). « Réglées » : sans période, les 300
 * règlements les plus récents et l'écran le dit (`reglees_plafond`, `reglees_total`) ; avec une
 * période Du / Au — qui porte alors sur la **date de règlement** —, toutes celles de la période.
 */
import { Bascule } from '../../../composants/mise-en-page/Bascule'
import { Carte } from '../../../composants/mise-en-page/Carte'
import { Indicateurs } from '../../../composants/mise-en-page/Indicateurs'
import { Chargement } from '../../../composants/retour/Chargement'
import { Erreur } from '../../../composants/retour/Erreur'
import { Kpi } from '../../../composants/retour/Kpi'
import { Note } from '../../../composants/retour/Note'
import { DateChamp } from '../../../composants/saisie/DateChamp'
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { DataTable } from '../../../composants/tableaux/DataTable'
import { formule } from '../../../lib/aide'
import { date, mois, montant, montantCourt, nombre } from '../../../lib/format'
import { moisCourant } from '../../../lib/heure'
import { useSession } from '../../../lib/session'
import { useEtatListe } from '../../catalogue/etatListe'
import styles from '../analyse.module.css'
import { ChoixListe, Criteres, DateFiltre } from '../briques'
import { useEcheancier } from '../donnees'
import type { Echeancier as E, EcheanceLigne } from '../types'
import { colonnesEcheances, type VueEcheancier } from './colonnes'

const VUES: readonly VueEcheancier[] = ['echeances', 'mois', 'a_dater', 'reglees']

interface Mois {
  mois: string
  montant: number
}

const COLONNES_MOIS: readonly Colonne<Mois>[] = [
  {
    cle: 'mois',
    titre: 'Mois',
    rendu: (m) => <span className={m.mois < moisCourant() ? styles.retard : undefined}>{mois(m.mois)}</span>,
  },
  {
    cle: 'montant',
    titre: 'À payer (MAD)',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (m) => nombre(m.montant),
  },
]

function IndicateursEcheancier({ e, filtre }: { e: E; filtre: boolean }) {
  const suite = filtre ? ' (selon les filtres)' : ''
  return (
    <Indicateurs libelle="Indicateurs de l’échéancier">
      <Kpi
        titre="À payer"
        valeur={montantCourt(e.total_mad, 'MAD')}
        exact={`${montant(e.total_mad, 'MAD')}${suite}`}
        detail={`${nombre(e.lignes.length)} échéance(s) connue(s)${suite}`}
        formule={formule('echeancier_a_payer')}
      />
      <Kpi
        titre="Échu, non réglé"
        valeur={montantCourt(e.echu_mad, 'MAD')}
        exact={montant(e.echu_mad, 'MAD')}
        ton={e.echu_mad > 0 ? 'critique' : 'ok'}
        detail={`${nombre(e.echues)} échéance(s) dépassée(s)`}
        formule={formule('echeancier_echu')}
      />
      <Kpi
        titre="Dans les 30 jours"
        valeur={montantCourt(e.dans_30_jours_mad, 'MAD')}
        exact={montant(e.dans_30_jours_mad, 'MAD')}
        ton={e.dans_30_jours_mad > 0 ? 'attention' : undefined}
        detail="à payer d’ici trente jours"
        formule={formule('echeancier_30_jours')}
      />
      <Kpi
        titre="À dater"
        valeur={montantCourt(e.a_dater_mad, 'MAD')}
        exact={montant(e.a_dater_mad, 'MAD')}
        ton={e.a_dater.length ? 'attention' : undefined}
        detail={`${nombre(e.a_dater.length)} facture(s) ou frais sans échéance`}
        formule={formule('echeancier_a_dater')}
      />
    </Indicateurs>
  )
}

/** Les filtres du serveur, posés dans la barre d'outils. */
function Outils({ etat, n }: { etat: ReturnType<typeof useEtatListe>; n: number }) {
  const du = etat.lire('du')
  const au = etat.lire('au')
  return (
    <>
      <ChoixListe
        libelle="Nature"
        valeur={etat.lire('nature')}
        options={[
          { valeur: '', libelle: 'Toutes les échéances' },
          { valeur: 'facture', libelle: 'Factures des fournisseurs' },
          { valeur: 'frais', libelle: 'Frais d’importation' },
        ]}
        onChange={(v) => etat.choix.poser('nature', v || null)}
      />
      <DateFiltre
        libelle="Du"
        titre="Échéances à partir de ce jour ; vue Réglées : règlements à partir de ce jour"
      >
        <DateChamp
          libelle="Du"
          valeur={du}
          max={au || undefined}
          futurPermis={!au}
          onChange={(v) => etat.choix.poser('du', v || null)}
        />
      </DateFiltre>
      <DateFiltre
        libelle="Au"
        titre="Échéances jusqu’à ce jour inclus ; vue Réglées : règlements jusqu’à ce jour inclus"
      >
        <DateChamp
          libelle="Au"
          valeur={au}
          min={du || undefined}
          futurPermis
          onChange={(v) => etat.choix.poser('au', v || null)}
        />
      </DateFiltre>
      <Criteres nombre={n} onEffacer={etat.choix.effacer} />
    </>
  )
}

const VIDES: Record<VueEcheancier, string> = {
  echeances:
    'Aucune échéance connue : elles viennent de l’échéance des factures (réceptions) et des frais d’importation.',
  mois: 'Rien à payer.',
  a_dater: 'Toutes les factures et tous les frais connus ont leur échéance.',
  reglees: 'Aucun règlement noté : « Réglée… » sur une échéance le note.',
}

const TRI: Partial<Record<VueEcheancier, { cle: string; sens: 1 | -1 }>> = {
  echeances: { cle: 'date', sens: 1 },
  reglees: { cle: 'payee_le', sens: -1 },
}

/** Les pièces écartées (réception ou dossier annulés) : une ligne, le détail en infobulle. */
function Ecartees({ e }: { e: E }) {
  if (!e.ecartees.length) return null
  const detail = e.ecartees
    .slice(0, 6)
    .map((x) => `${x.piece} (${x.tiers}) : ${x.raison ?? ''}`)
    .join(' · ')
  return (
    <Note uneLigne={detail}>
      {`${nombre(e.ecartees.length)} facture(s) ou frais ne sont plus dus (réception ou dossier annulés) : les détacher, ou faire établir un avoir.`}
    </Note>
  )
}

type Reglees = Pick<E, 'reglees' | 'reglees_plafond' | 'reglees_total'>

/** Les réglées sont-elles plafonnées (sans période, au-delà de 300 règlements) ? */
export function plafonnees(e: Reglees): boolean {
  return e.reglees_plafond !== null && e.reglees_total > e.reglees_plafond
}

/**
 * Ce que la vue « Réglées » porte, toujours dit : « les 300 dernières sur 1 540 » et comment les
 * voir toutes, ou « toutes celles réglées du … au … » (la période porte sur la date de règlement).
 */
export function mentionReglees(e: Reglees, du: string, au: string): string {
  const n = nombre(e.reglees_total)
  if (e.reglees_plafond === null) {
    const bornes = [du && `du ${date(du)}`, au && `au ${date(au)}`].filter(Boolean).join(' ')
    return `Réglées : toutes les pièces réglées ${bornes} (${n}, date de règlement).`
  }
  const p = nombre(e.reglees_plafond)
  if (!plafonnees(e)) {
    return `Réglées : toutes (${n}). Au-delà de ${p}, seules les ${p} dernières paraissent sans période (Du / Au, date de règlement).`
  }
  return `Réglées : les ${p} dernières sur ${n}. Pour toutes les voir, poser une période (Du / Au) : elle s’applique à la date de règlement.`
}

function Vues({ e, vue, onChange }: { e: E; vue: VueEcheancier; onChange: (v: VueEcheancier) => void }) {
  const reglees = plafonnees(e) ? `les ${nombre(e.reglees_plafond ?? 0)} dernières` : nombre(e.reglees.length)
  return (
    <Bascule
      libelle="Vue de l’échéancier"
      vues={[
        {
          cle: 'echeances',
          libelle: `Échéances (${nombre(e.lignes.length)} · ${montantCourt(e.total_mad, 'MAD')})`,
        },
        { cle: 'mois', libelle: 'Par mois' },
        { cle: 'a_dater', libelle: `À dater (${nombre(e.a_dater.length)})` },
        { cle: 'reglees', libelle: `Réglées (${reglees})` },
      ]}
      valeur={vue}
      onChange={onChange}
    />
  )
}

interface TableauProps {
  e: E
  vue: VueEcheancier
  etat: ReturnType<typeof useEtatListe>
  n: number
}

function Tableau({ e, vue, etat, n }: TableauProps) {
  const { role } = useSession()
  const commun = {
    recherche: etat.recherche,
    serveur: true,
    placeholder: 'Fournisseur, prestataire, n° de pièce…',
    exporter: {
      route: '/export/echeancier',
      parametres: { nature: etat.lire('nature'), du: etat.lire('du'), au: etat.lire('au') },
    },
    outils: <Outils etat={etat} n={n} />,
    vide: VIDES[vue],
    triInitial: TRI[vue],
  }
  if (vue === 'mois') {
    const parMois = Object.entries(e.par_mois).map(([m, total]) => ({ mois: m, montant: total }))
    return (
      <DataTable<Mois>
        libelle="À payer par mois"
        lignes={parMois}
        colonnes={COLONNES_MOIS}
        cle={(m) => m.mois}
        {...commun}
      />
    )
  }
  const lignes = { echeances: e.lignes, a_dater: e.a_dater, reglees: e.reglees }[vue]
  return (
    <DataTable<EcheanceLigne>
      libelle={`Échéancier — ${vue}`}
      lignes={lignes}
      colonnes={colonnesEcheances(vue, role, role === 'direction')}
      cle={(l) => `${l.objet}-${l.id}`}
      {...commun}
    />
  )
}

export function Echeancier() {
  const etat = useEtatListe('eq', ['nature', 'du', 'au'])
  const lu = useEcheancier({
    q: etat.recherche.valeur,
    nature: etat.lire('nature'),
    du: etat.lire('du'),
    au: etat.lire('au'),
  })
  const vue = VUES.find((v) => v === etat.lire('evue')) ?? 'echeances'
  if (lu.isPending) return <Chargement quoi="l’échéancier" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const e = lu.data
  const n = Object.keys(etat.choix.valeurs).length + (etat.recherche.valeur.trim() ? 1 : 0)
  return (
    <>
      <IndicateursEcheancier e={e} filtre={n > 0} />
      <Ecartees e={e} />
      {vue === 'reglees' ? (
        <Note ton={plafonnees(e) ? 'attention' : 'info'}>
          {mentionReglees(e, etat.lire('du'), etat.lire('au'))}
        </Note>
      ) : null}
      <Carte
        titre="Ce qu’il faudra payer"
        actions={
          <Vues e={e} vue={vue} onChange={(v) => etat.choix.poser('evue', v === 'echeances' ? null : v)} />
        }
        serre
        remplir
        className={styles.carteListe}
      >
        <Tableau e={e} vue={vue} etat={etat} n={n} />
      </Carte>
    </>
  )
}
