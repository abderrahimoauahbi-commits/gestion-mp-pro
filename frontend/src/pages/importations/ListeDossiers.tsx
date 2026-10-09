/**
 * Importations › Dossiers ouverts · Dossiers clos (· Annulés) (ECRANS-PRO 5.2) : recherche à la
 * frappe (numéro, libellé, banque, observations, factures, réceptions, familles, fournisseurs) et
 * filtres liés (fournisseur, « à vérifier seulement ») dans l'adresse, tableau dans son cadre, pied
 * « Total des N dossiers affichés » (il suit la recherche, anomalie 5.9), export avec la vue.
 */
import { useMemo, type ReactNode } from 'react'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Bouton } from '../../composants/saisie/Bouton'
import { champsCherches, piedDeColonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { passe, trouve, type Filtre } from '../../composants/tableaux/filtrage'
import { nombre } from '../../lib/format'
import { colonnesDossiers } from './colonnesDossiers'
import type { EtatListe } from './etatPage'
import styles from './Importations.module.css'
import type { DossierResume } from './types'

type Statut = 'ouvert' | 'clos' | 'annule'

/** Les filtres liés : le fournisseur par son identifiant (celui que lit l'export), « à vérifier ». */
function filtres(lignes: readonly DossierResume[]): Filtre<DossierResume>[] {
  const noms = new Map(
    lignes.flatMap((d) => (d.facture ? [[String(d.facture.fournisseur_id), d.facture.fournisseur]] : [])),
  )
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (d) => (d.facture ? String(d.facture.fournisseur_id) : null),
      libelleValeur: (v) => noms.get(v) ?? v,
    },
    {
      cle: 'verifier',
      libelle: 'À vérifier',
      valeur: (d) => (d.a_verifier.length ? 'oui' : 'non'),
      libelleValeur: (v) => (v === 'oui' ? 'À vérifier seulement' : 'Sans alerte'),
    },
  ]
}

const cache = (d: DossierResume) => [d.familles.map((f) => f.famille), d.fournisseurs]

/** Le pied « Total des N dossiers affichés » : les lignes qui passent la recherche et les filtres. */
function Pied({
  lignes,
  etat,
  statut,
}: {
  lignes: readonly DossierResume[]
  etat: EtatListe
  statut: Statut
}) {
  const colonnes = colonnesDossiers(statut)
  const q = etat.recherche.valeur
  const visibles = lignes.filter(
    (d) =>
      passe(d, filtres(lignes), etat.choix.valeurs) &&
      (!q.trim() || trouve(champsCherches(colonnes, d, cache), q)),
  )
  if (visibles.length < 2) return null
  return (
    <tr className={styles.totaux}>
      {colonnes.map((c, i) => (
        <td key={c.cle} className={c.droite ? styles.chiffre : undefined}>
          {i === 0 ? `Total des ${nombre(visibles.length)} dossiers affichés` : piedDeColonne(c, visibles)}
        </td>
      ))}
    </tr>
  )
}

export interface ListeDossiersProps {
  statut: Statut
  lignes: readonly DossierResume[]
  chargement: boolean
  etat: EtatListe
  ouvrir: (id: number) => void
  /** L'onglet des clos : la bascule « Clos » / « Annulés ». */
  bascule?: { annules: boolean; choisir: (annules: boolean) => void }
  /** Les arrivées qui attendent leur dossier (onglet des ouverts). */
  enAttente?: { nombre: number; voir: () => void }
  erreur?: ReactNode
}

const VIDES: Record<Statut, string> = {
  ouvert: 'Aucun dossier ouvert. « Nouveau dossier » en ouvre un depuis une facture.',
  clos: 'Aucun dossier clos.',
  annule: 'Aucun dossier annulé.',
}

const TITRES: Record<Statut, string> = {
  ouvert: 'Dossiers ouverts',
  clos: 'Dossiers clos',
  annule: 'Dossiers annulés',
}

export function ListeDossiers(p: ListeDossiersProps) {
  const colonnes = useMemo(() => colonnesDossiers(p.statut), [p.statut])
  const lesFiltres = useMemo(() => filtres(p.lignes), [p.lignes])
  const actions = (
    <>
      {p.enAttente?.nombre ? (
        <Bouton variante="fantome" taille="petit" onClick={p.enAttente.voir}>
          {nombre(p.enAttente.nombre)} arrivée(s) attendent leur dossier
        </Bouton>
      ) : null}
      {p.bascule ? (
        <Bascule
          libelle="Dossiers clos ou annulés"
          valeur={p.bascule.annules ? 'annules' : 'clos'}
          onChange={(v) => p.bascule?.choisir(v === 'annules')}
          vues={[
            { cle: 'clos', libelle: 'Clos' },
            { cle: 'annules', libelle: 'Annulés', titre: 'Les dossiers annulés gardent leur numéro' },
          ]}
        />
      ) : null}
    </>
  )
  return (
    <Carte titre={TITRES[p.statut]} actions={actions} serre remplir>
      {p.erreur ?? (
        <DataTable
          libelle={TITRES[p.statut]}
          lignes={p.lignes}
          colonnes={colonnes}
          cle={(d) => d.id}
          cliquable={(d) => p.ouvrir(d.id)}
          recherche={p.etat.recherche}
          choix={p.etat.choix}
          filtres={lesFiltres}
          rechercheCachee={cache}
          placeholder="Numéro, libellé, facture, réception, famille de fil (« frisé 2900 »)…"
          pied={<Pied lignes={p.lignes} etat={p.etat} statut={p.statut} />}
          exporter={{ route: '/export/dossiers', parametres: { statut: p.statut } }}
          vide={
            p.chargement
              ? 'Chargement des dossiers…'
              : p.etat.recherche.valeur
                ? 'Aucun dossier ne correspond à la recherche.'
                : VIDES[p.statut]
          }
        />
      )}
    </Carte>
  )
}
