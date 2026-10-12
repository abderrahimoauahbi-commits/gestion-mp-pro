/**
 * Importations › Dossiers ouverts · Dossiers clos (· Annulés) (ECRANS-PRO 5.2) : la liste est
 * **paginée au serveur** (recherche tolérante à la ponctuation, filtres liés et pied poussés en
 * SQL/au moteur ; mêmes chiffres qu'avant). Recherche à la frappe (numéro, libellé, banque,
 * observations, factures, réceptions, familles, fournisseurs) et filtres (fournisseur d'une de ses
 * factures, « à vérifier ») dans l'adresse, tableau dans son cadre, pied « Total des N dossiers
 * affichés » (il suit la recherche, anomalie 5.9), export avec la vue.
 */
import { useMemo } from 'react'

import { Bascule } from '../../composants/mise-en-page/Bascule'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { kg, montant, nombre } from '../../lib/format'
import { colonnesDossiers } from './colonnesDossiers'
import { useApercuDossiers } from './donnees'
import type { EtatListe } from './etatPage'
import styles from './Importations.module.css'
import type { ApercuDossiers, DossierResume } from './types'

type Statut = 'ouvert' | 'clos' | 'annule'

const LIBELLE_VERIFIER: Record<string, string> = {
  oui: 'À vérifier seulement',
  non: 'Sans alerte',
}

/** Les paramètres de la route 187 : l'onglet, la recherche et les filtres liés. */
function parametres(statut: Statut, etat: EtatListe) {
  const choix = etat.choix.valeurs
  return {
    statut,
    q: etat.recherche.valeur.trim() || undefined,
    fournisseur: choix.fournisseur || undefined,
    verifier: choix.verifier || undefined,
  }
}

/** Les filtres liés, appliqués **au serveur** : le fournisseur d'une facture (options de l'aperçu),
 * « à vérifier » (oui/non). Leurs valeurs sont celles qu'envoient la route et l'export. */
function filtres(apercu?: ApercuDossiers): Filtre<DossierResume>[] {
  const noms = new Map((apercu?.fournisseurs ?? []).map((f) => [String(f.id), f.nom]))
  return [
    {
      cle: 'fournisseur',
      libelle: 'Fournisseur',
      valeur: (d) => (d.factures[0] ? String(d.factures[0].fournisseur_id) : null),
      libelleValeur: (v) => noms.get(v) ?? v,
      options: (apercu?.fournisseurs ?? []).map((f) => String(f.id)),
    },
    {
      cle: 'verifier',
      libelle: 'À vérifier',
      valeur: (d) => (d.a_verifier.length ? 'oui' : 'non'),
      libelleValeur: (v) => LIBELLE_VERIFIER[v] ?? v,
      options: ['oui', 'non'],
    },
  ]
}

/** Le pied « Total des N dossiers affichés » : les totaux du serveur sous leurs colonnes. */
function Pied({ colonnes, apercu }: { colonnes: Colonne<DossierResume>[]; apercu?: ApercuDossiers }) {
  if (!apercu || apercu.nombre < 2) return null
  const totaux: Partial<Record<string, number>> = {
    poids: apercu.poids,
    marchandise_mad: apercu.marchandise_mad,
    charges_mad: apercu.charges_mad,
    revient_mad: apercu.revient_mad,
    decaisse_mad: apercu.decaisse_mad,
  }
  const total = (cle: string): number | undefined => totaux[cle]
  return (
    <tr className={styles.totaux}>
      {colonnes.map((c, i) => {
        const v = total(c.cle)
        return (
          <td key={c.cle} className={c.droite ? styles.chiffre : undefined}>
            {i === 0
              ? `Total des ${nombre(apercu.nombre)} dossiers affichés`
              : v == null
                ? ''
                : c.unite === 'kg'
                  ? kg(v)
                  : montant(v, 'MAD')}
          </td>
        )
      })}
    </tr>
  )
}

export interface ListeDossiersProps {
  statut: Statut
  etat: EtatListe
  ouvrir: (id: number) => void
  /** L'onglet des clos : la bascule « Clos » / « Annulés ». */
  bascule?: { annules: boolean; choisir: (annules: boolean) => void }
  /** Les arrivées qui attendent leur dossier (onglet des ouverts). */
  enAttente?: { nombre: number; voir: () => void }
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
  const params = parametres(p.statut, p.etat)
  const liste = useListePaginee<DossierResume>('/dossiers', params)
  const apercu = useApercuDossiers(params)
  const colonnes = useMemo(() => colonnesDossiers(p.statut), [p.statut])
  const lesFiltres = useMemo(() => filtres(apercu.data), [apercu.data])
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
      {liste.requete.isError ? (
        <Erreur erreur={liste.requete.error} onReessayer={() => void liste.requete.refetch()} />
      ) : (
        <DataTable<DossierResume>
          libelle={TITRES[p.statut]}
          serveur
          lignes={liste.lignes}
          total={liste.total}
          chargerPlus={liste.chargerPlus}
          colonnes={colonnes}
          cle={(d) => d.id}
          cliquable={(d) => p.ouvrir(d.id)}
          recherche={p.etat.recherche}
          choix={p.etat.choix}
          filtres={lesFiltres}
          placeholder="Numéro, libellé, facture, réception, famille de fil (« frisé 2900 »)…"
          pied={liste.lignes.length ? <Pied colonnes={colonnes} apercu={apercu.data} /> : undefined}
          exporter={{ route: '/export/dossiers', parametres: { statut: p.statut } }}
          vide={
            liste.requete.isPending
              ? 'Chargement des dossiers…'
              : p.etat.recherche.valeur.trim()
                ? 'Aucun dossier ne correspond à la recherche.'
                : VIDES[p.statut]
          }
        />
      )}
    </Carte>
  )
}
