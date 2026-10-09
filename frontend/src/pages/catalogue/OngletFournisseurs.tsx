/**
 * Onglet « Fournisseurs » (`/catalogue?onglet=fournisseurs` ; direction, achats) : le délai et la
 * couverture règlent le plan d'achat. Recherche sur tous les champs de la fiche, filtres liés
 * (origine, devise) et état, avec leurs propres noms dans l'adresse (`fq`, `origine`, `devise`,
 * `fetat`) ; une ligne ouvre la fiche (`/fournisseurs/:id`). OTIF rapproché par identifiant.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Badge } from '../../composants/retour/Badge'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { ExportExcel } from '../../composants/tableaux/ExportExcel'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { jours, nombre, part, VIDE } from '../../lib/format'
import styles from './catalogue.module.css'
import { ChoixEtat } from './ChoixEtat'
import { deux } from './colonnesMatieres'
import { useFournisseurs } from './donnees'
import { lireEtat, passeEtat, useEtatListe } from './etatListe'
import { scoreDe, usePerformance, type Performance } from './performance'
import { estComplet, type Fournisseur } from './types'

export const CLES_FOURNISSEURS = ['origine', 'devise', 'fetat'] as const

function Devises({ f }: { f: Fournisseur }) {
  const liste = Object.entries(f.devises)
  if (!liste.length) return <span className={styles.note}>{f.devise} (par défaut)</span>
  return (
    <span className={styles.rangee} title="un bon de commande par devise">
      {liste.map(([d, n]) => (
        <Badge key={d} ton={d === f.devise ? 'accent' : 'neutre'}>{`${d} · ${nombre(n)}`}</Badge>
      ))}
    </span>
  )
}

function Nom({ f }: { f: Fournisseur }) {
  return deux(
    <>
      <span className={f.actif ? styles.fort : styles.eteinte}>{f.nom}</span>
      {f.actif ? null : (
        <>
          {' '}
          <Badge ton="neutre">désactivé</Badge>
        </>
      )}
    </>,
    f.code,
  )
}

function Delai({ f }: { f: Fournisseur }) {
  const aide = `Moyenne commande → réception validée, sur ${nombre(f.livraisons_mesurees)} livraison(s) en douze mois`
  return deux(
    jours(f.delai_jours),
    f.delai_mesure_jours != null ? <span title={aide}>mesuré {jours(f.delai_mesure_jours)}</span> : null,
  )
}

const paiement = (f: Fournisseur) =>
  [f.mode_paiement, f.delai_paiement_jours ? jours(f.delai_paiement_jours) : '']
    .filter(Boolean)
    .join(' · ') || VIDE

const AVANT: readonly Colonne<Fournisseur>[] = [
  { cle: 'nom', titre: 'Fournisseur', rendu: (f) => <Nom f={f} /> },
  { cle: 'pays', titre: 'Pays', valeur: (f) => f.pays || 'MAROC' },
  {
    cle: 'devises',
    titre: 'Devises',
    valeur: (f) => Object.keys(f.devises).join(' ') || f.devise,
    rendu: (f) => <Devises f={f} />,
  },
  { cle: 'delai_jours', titre: 'Délai', droite: true, rendu: (f) => <Delai f={f} /> },
  {
    cle: 'couverture_commande_jours',
    titre: 'Couverture',
    valeur: (f) =>
      f.couverture_commande_jours ? jours(f.couverture_commande_jours) : `${VIDE} (réglage général)`,
  },
  { cle: 'mode_paiement', titre: 'Paiement', rendu: (f) => deux(paiement(f), f.conditions_paiement) },
  { cle: 'incoterm', titre: 'Incoterm', rendu: (f) => deux(f.incoterm || VIDE, f.port_chargement) },
]

const APRES: readonly Colonne<Fournisseur>[] = [
  { cle: 'nb_matieres', titre: 'Matières', droite: true },
  {
    cle: 'contact',
    titre: 'Contact',
    rendu: (f) => deux(f.contact || VIDE, [f.telephone, f.email].filter(Boolean).join(' · ')),
  },
]

/** L'OTIF, rapproché par identifiant (« — » tant que rien n'est noté). */
function colonneOtif(perf: Performance | undefined): Colonne<Fournisseur> {
  return {
    cle: 'otif',
    titre: 'OTIF',
    aide: 'Livraisons à l’heure, complètes et conformes',
    valeur: (f) => scoreDe(perf, f.id)?.otif ?? null,
    rendu: (f) => {
      const s = scoreDe(perf, f.id)
      if (s?.otif == null) return VIDE
      const ton = s.otif >= (perf?.cible_otif ?? 0) ? 'ok' : 'critique'
      return <Badge ton={ton}>{`${part(s.otif, 0)} · ${nombre(s.receptions)} réc.`}</Badge>
    },
  }
}

function colonnes(perf: Performance | undefined): Colonne<Fournisseur>[] {
  return [...AVANT, colonneOtif(perf), ...APRES]
}

const FILTRES: Filtre<Fournisseur>[] = [
  {
    cle: 'origine',
    libelle: 'Origine',
    valeur: (f) => (f.local ? 'Locaux (Maroc)' : 'Étrangers (importation)'),
  },
  { cle: 'devise', libelle: 'Devise', valeur: (f) => f.devise },
]

const CHERCHES = (f: Fournisseur) => [
  f.code,
  f.contact,
  f.telephone,
  f.email,
  f.devise,
  f.incoterm,
  f.mode_paiement,
  f.conditions_paiement,
  f.port_chargement,
  f.banque,
  f.notes,
]

export function OngletFournisseurs({ onOuvrir }: { onOuvrir: (id: number | 'nouveau') => void }) {
  const lu = useFournisseurs()
  const perf = usePerformance()
  const etatListe = useEtatListe('fq', CLES_FOURNISSEURS)
  const etat = lireEtat(etatListe.lire('fetat'))
  const tous = useMemo(() => (lu.data ?? []).filter(estComplet), [lu.data])
  const lignes = useMemo(() => tous.filter((f) => passeEtat(f.actif, etat)), [tous, etat])
  const cols = useMemo(() => colonnes(perf.data), [perf.data])
  const actions = (
    <>
      <ExportExcel route="/export/fournisseurs/fiches" />
      <Bouton variante="principal" icone="plus" onClick={() => onOuvrir('nouveau')}>
        Nouveau fournisseur
      </Bouton>
    </>
  )
  return (
    <Carte
      titre="Fournisseurs"
      sous="Le délai et la couverture règlent le plan d’achat."
      actions={actions}
      serre
      remplir
    >
      {lu.isPending ? <Chargement quoi="les fournisseurs" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.data ? (
        <DataTable<Fournisseur>
          libelle="Fournisseurs"
          lignes={lignes}
          colonnes={cols}
          filtres={FILTRES}
          cle={(f) => f.id}
          recherche={etatListe.recherche}
          choix={etatListe.choix}
          rechercheCachee={CHERCHES}
          placeholder="Nom, pays, contact, devise, incoterm, port, banque…"
          triInitial={{ cle: 'nom', sens: 1 }}
          cliquable={(f) => onOuvrir(f.id)}
          vide={tous.length ? 'Aucun fournisseur dans cet état.' : 'Aucun fournisseur pour le moment.'}
          outils={
            <ChoixEtat
              valeur={etatListe.lire('fetat')}
              onChange={(v) => etatListe.choix.poser('fetat', v)}
              libelles={['Fournisseurs actifs', 'Actifs et désactivés', 'Désactivés seulement']}
            />
          }
        />
      ) : null}
    </Carte>
  )
}
