/**
 * Analyse › Fournisseurs (`/analyse?onglet=fournisseurs`) : le classement des fournisseurs sur
 * leurs livraisons (OTIF, retours, délai, score sur 100), sans émoji (P8-23) ; « À surveiller »
 * est un nom de classement, affiché tel quel (ECRANS-PRO § 5 E7). Un clic ouvre « ses
 * réceptions » à adresse stable (`&fournisseur=ID`, lien de la fiche fournisseur, P8-1).
 * Adresse : `fq` (recherche), `tous` (ceux sans commande).
 */
import { useMemo } from 'react'
import { useSearchParams } from 'react-router'

import { LienDocument } from '../../composants/documents/LienDocument'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { avecParametre } from '../../lib/adresse'
import { formule } from '../../lib/aide'
import { date, jours, montant, montantCourt, nombre, part, partSignee, VIDE } from '../../lib/format'
import type { Ton } from '../../lib/statuts'
import { useEtatListe } from '../catalogue/etatListe'
import styles from './analyse.module.css'
import { Case, Criteres } from './briques'
import { usePerformance } from './donnees'
import type { PerformanceFournisseurs, ReceptionNotee, ScoreFournisseur } from './types'

/** Le ton d'un classement (table unique `statuts.classement`). */
export function tonClassement(classement: string): Ton {
  if (/strat/i.test(classement)) return 'ok'
  if (/surveiller/i.test(classement)) return 'attention'
  if (/challenger/i.test(classement)) return 'critique'
  return 'neutre'
}

const COLONNES: readonly Colonne<ScoreFournisseur>[] = [
  {
    cle: 'fournisseur',
    titre: 'Fournisseur',
    recherche: (x) => [x.pays, x.devise, x.classement, x.action],
    rendu: (x) => (
      <>
        <strong>{x.fournisseur}</strong>
        <span className={styles.dessous}>{[x.pays, x.devise].filter(Boolean).join(' · ')}</span>
      </>
    ),
  },
  { cle: 'delai_jours', titre: 'Délai', droite: true, rendu: (x) => jours(x.delai_jours) },
  { cle: 'nb_commandes', titre: 'Commandes', droite: true },
  {
    cle: 'montant_mad',
    titre: 'Acheté (MAD)',
    droite: true,
    unite: 'MAD',
    total: true,
    rendu: (x) => nombre(x.montant_mad),
  },
  { cle: 'receptions', titre: 'Réceptions', droite: true },
  {
    cle: 'on_time',
    titre: 'À l’heure',
    aide: 'Livrées à la date promise',
    droite: true,
    rendu: (x) => part(x.on_time, 0),
  },
  {
    cle: 'in_full',
    titre: 'Complètes',
    aide: 'Chaque ligne livrée en entier',
    droite: true,
    rendu: (x) => part(x.in_full, 0),
  },
  {
    cle: 'in_spec',
    titre: 'Conformes',
    aide: 'Toutes les lignes jugées conformes (ni réserve ni refus)',
    droite: true,
    rendu: (x) => part(x.in_spec, 0),
  },
  {
    cle: 'otif',
    titre: 'OTIF',
    droite: true,
    rendu: (x) =>
      x.otif == null ? VIDE : <Badge ton={x.sous_performant ? 'attention' : 'ok'}>{part(x.otif, 0)}</Badge>,
  },
  {
    cle: 'taux_retours',
    titre: 'Retours',
    droite: true,
    rendu: (x) => (x.taux_retours ? part(x.taux_retours) : VIDE),
  },
  {
    cle: 'ecart_pesee_moyen',
    titre: 'Écart de pesée',
    droite: true,
    rendu: (x) => partSignee(x.ecart_pesee_moyen),
  },
  {
    cle: 'score',
    titre: 'Score',
    droite: true,
    rendu: (x) => <strong>{x.score == null ? VIDE : nombre(x.score)}</strong>,
  },
  {
    cle: 'classement',
    titre: 'Classement',
    rendu: (x) =>
      x.score == null ? (
        <span className={styles.note}>pas encore noté</span>
      ) : (
        <>
          <Badge ton={tonClassement(x.classement)}>{x.classement}</Badge>
          <span className={styles.dessous}>{x.action}</span>
        </>
      ),
  },
]

function IndicateursFournisseurs({ p }: { p: PerformanceFournisseurs }) {
  const notes = p.lignes.filter((x) => x.otif != null)
  const sous = p.lignes.filter((x) => x.sous_performant)
  const notees = p.receptions.filter((r) => r.otif != null)
  const otif = notees.length ? notees.reduce((s, r) => s + (r.otif ?? 0), 0) / notees.length : null
  return (
    <Indicateurs libelle="Indicateurs des fournisseurs">
      <Kpi
        titre="Livraisons parfaites (OTIF)"
        valeur={part(otif, 0)}
        ton={otif == null ? undefined : otif >= p.cible_otif ? 'ok' : 'attention'}
        detail={`à l’heure, complètes et conformes · cible ${part(p.cible_otif, 0)}`}
        formule={formule('otif')}
      />
      <Kpi
        titre="Sous la cible"
        valeur={nombre(sous.length)}
        ton={sous.length ? 'attention' : 'ok'}
        detail={
          sous
            .slice(0, 3)
            .map((x) => x.fournisseur)
            .join(', ') || 'aucun fournisseur'
        }
        formule={formule('fournisseurs_sous_cible')}
      />
      <Kpi
        titre="Réceptions notées"
        valeur={nombre(notees.length)}
        detail={`sur ${nombre(p.receptions.length)} réception(s) validée(s)`}
        formule={formule('fournisseurs_receptions_notees')}
      />
      <Kpi
        titre="Fournisseurs notés"
        valeur={`${nombre(notes.length)} / ${nombre(p.lignes.length)}`}
        detail={`stratégique dès ${nombre(p.seuils.strategique)}/100`}
        formule={formule('fournisseurs_notes')}
      />
    </Indicateurs>
  )
}

const ouiNon = (v: number | null | undefined) => (v == null ? VIDE : v ? 'Oui' : 'Non')

const COLONNES_RECEPTIONS: readonly Colonne<ReceptionNotee>[] = [
  {
    cle: 'numero',
    titre: 'Réception',
    rendu: (r) => <LienDocument genre="reception" id={r.reception_id} numero={r.numero} />,
  },
  { cle: 'date_reception', titre: 'Date', rendu: (r) => date(r.date_reception) },
  { cle: 'on_time', titre: 'À l’heure', droite: true, rendu: (r) => ouiNon(r.on_time) },
  { cle: 'in_full', titre: 'Complète', droite: true, rendu: (r) => ouiNon(r.in_full) },
  { cle: 'in_spec', titre: 'Conforme', droite: true, rendu: (r) => ouiNon(r.in_spec) },
  {
    cle: 'otif',
    titre: 'Parfaite',
    droite: true,
    rendu: (r) =>
      r.otif == null ? VIDE : <Badge ton={r.otif ? 'ok' : 'attention'}>{r.otif ? 'Oui' : 'Non'}</Badge>,
  },
  { cle: 'lignes_hors_tolerance', titre: 'Lignes hors tolérance', droite: true },
  { cle: 'ecart_pesee', titre: 'Écart de pesée', droite: true, rendu: (r) => partSignee(r.ecart_pesee) },
]

function NoteFournisseur({ score }: { score: ScoreFournisseur }) {
  return (
    <Indicateurs libelle="Note du fournisseur">
      <Kpi
        titre="Score"
        valeur={score.score == null ? VIDE : `${nombre(score.score)} / 100`}
        detail={score.classement}
        formule={formule('otif')}
      />
      <Kpi
        titre="OTIF"
        valeur={part(score.otif, 0)}
        ton={score.sous_performant ? 'attention' : undefined}
        formule={formule('otif')}
      />
      <Kpi
        titre="Acheté"
        valeur={montantCourt(score.montant_mad, 'MAD')}
        exact={montant(score.montant_mad, 'MAD')}
        detail={`${nombre(score.nb_commandes)} commande(s)`}
        formule={formule('fournisseurs_achete')}
      />
      <Kpi titre="Action conseillée" valeur={score.action || VIDE} formule={formule('fournisseurs_action')} />
    </Indicateurs>
  )
}

function SesReceptions({
  p,
  id,
  onFermer,
}: {
  p: PerformanceFournisseurs
  id: number
  onFermer: () => void
}) {
  const score = p.lignes.find((x) => x.fournisseur_id === id)
  const receptions = p.receptions.filter((r) => r.fournisseur_id === id)
  return (
    <Fenetre
      titre={`${score?.fournisseur ?? 'Fournisseur'} — ses réceptions`}
      taille="large"
      onFermer={onFermer}
    >
      {score ? (
        <NoteFournisseur score={score} />
      ) : (
        <Note ton="attention">
          Ce fournisseur n’est pas dans le classement (aucune commande ni réception).
        </Note>
      )}
      <DataTable<ReceptionNotee>
        libelle="Réceptions notées"
        lignes={receptions}
        colonnes={COLONNES_RECEPTIONS}
        cle={(r) => r.reception_id ?? r.numero}
        recherche={false}
        hauteur="fenetre"
        triInitial={{ cle: 'date_reception', sens: -1 }}
        vide="Aucune réception validée pour ce fournisseur."
      />
      <Note>
        « — » dans « À l’heure » : la commande ne portait pas de date de livraison promise ; la réception
        compte alors comme à l’heure. « — » dans « Complète » : la réception ne devait rien (hors commande, ou
        bon déjà livré) ; elle n’entre pas dans l’OTIF.
      </Note>
    </Fenetre>
  )
}

export function Fournisseurs() {
  const lu = usePerformance()
  const [params, setParams] = useSearchParams()
  const etat = useEtatListe('fq', ['tous'])
  const tous = etat.lire('tous') === '1'
  const ouvert = Number(params.get('fournisseur')) || null
  const lignes = useMemo(
    () => (lu.data?.lignes ?? []).filter((x) => tous || x.nb_commandes > 0),
    [lu.data, tous],
  )
  if (lu.isPending) return <Chargement quoi="le classement des fournisseurs" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const ouvrir = (id: number | null) =>
    setParams((p) => avecParametre(p, 'fournisseur', id == null ? null : String(id)))
  const n = (etat.recherche.valeur.trim() ? 1 : 0) + (tous ? 1 : 0)
  return (
    <>
      <IndicateursFournisseurs p={lu.data} />
      <Carte
        titre={`Le classement des fournisseurs — ${nombre(lignes.length)} affiché(s)`}
        serre
        remplir
        className={styles.carteListe}
      >
        <Note uneLigne="Score sur 100 : livraisons parfaites (OTIF) × 60 ; retours au fournisseur jusqu’à 20 points (20 sans retour, 0 dès 5 % de la matière reçue renvoyée) ; délai jusqu’à 20 points (20 jusqu’à 15 jours, un de moins par 5 jours au-delà). Une livraison est à l’heure si elle arrive à la date promise du bon (l’ETA ne la repousse pas), complète si toutes les lignes que le bon attendait encore sont livrées. Cliquer sur un fournisseur montre ses réceptions une à une.">
          Score sur 100 : OTIF × 60, retours jusqu’à 20 points, délai jusqu’à 20 points. Cliquer sur un
          fournisseur montre ses réceptions une à une.
        </Note>
        <DataTable<ScoreFournisseur>
          libelle="Classement des fournisseurs"
          lignes={lignes}
          colonnes={COLONNES}
          cle={(x) => x.fournisseur_id ?? x.fournisseur}
          recherche={etat.recherche}
          placeholder="Fournisseur, pays, classement… plusieurs mots"
          triInitial={{ cle: 'score', sens: -1 }}
          cliquable={(x) => ouvrir(x.fournisseur_id ?? null)}
          vide="Aucun fournisseur ne correspond."
          exporter={{ route: '/export/fournisseurs' }}
          outils={
            <>
              <Case valeur={tous} onChange={(v) => etat.choix.poser('tous', v ? '1' : null)}>
                montrer aussi ceux sans commande
              </Case>
              <Criteres nombre={n} onEffacer={etat.choix.effacer} />
            </>
          }
        />
      </Carte>
      {ouvert ? <SesReceptions p={lu.data} id={ouvert} onFermer={() => ouvrir(null)} /> : null}
    </>
  )
}
