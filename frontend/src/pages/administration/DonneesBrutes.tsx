/**
 * Administration › Données brutes (`/administration?onglet=donnees`, route 7 ; direction seule) :
 * les lignes d'une table métier telles qu'elles sont en base, pour la vérification indépendante
 * (liste fermée par le serveur : aucun compte, session, secret ni journal). `?table=` et `?date=`
 * (les tables datées ne rendent que ce qui existait ce soir-là).
 */
import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { DateChamp } from '../../composants/saisie/DateChamp'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { ChoixListe } from '../analyse/briques'
import { useEtatListe } from '../catalogue/etatListe'
import { valeurLisible } from './changements'
import styles from './administration.module.css'

type Donnees = Schema<'DonneesBrutes'>
type Ligne = Record<string, unknown> & { _rang: number }

/** La liste fermée du serveur (`services/donnees_brutes.TABLES`, relue par l'essai). */
export const TABLES: readonly string[] = [
  'matiere', 'fournisseur', 'devise', 'devise_cours', 'magasin', 'role_nomenclature', 'composition',
  'type_fil', 'titrage', 'couleur', 'code_douanier', 'poste_frais', 'motif', 'parametre', 'lot', 'solde',
  'mouvement', 'commande', 'commande_ligne', 'facture', 'reception', 'reception_ligne', 'dossier',
  'dossier_facture',
  'dossier_ligne', 'dossier_frais', 'dossier_frais_part', 'ordre', 'ordre_qualite', 'ordre_ligne',
  'ordre_prevu', 'operation', 'operation_ligne', 'qualite', 'qualite_poids', 'qualite_saison', 'recette',
  'recette_version', 'recette_version_ligne', 'recette_version_poids', 'plan_version', 'plan_version_saison',
  'metier', 'metier_etage', 'montage', 'montage_evenement', 'inventaire', 'inventaire_ligne',
  'inventaire_matiere', 'inventaire_critere', 'reclamation', 'indicateur_jour', 'parametre_historique',
  'commande_version', 'commande_version_ligne', 'commande_decision',
] // prettier-ignore

function colonnes(d: Donnees): Colonne<Ligne>[] {
  return d.colonnes.map((c) => ({
    cle: c,
    titre: c,
    valeur: (l) => {
      const v = l[c]
      return typeof v === 'number' || typeof v === 'string' || typeof v === 'boolean' ? v : null
    },
    rendu: (l) => valeurLisible(l[c]),
  }))
}

function Tableau({ table, date }: { table: string; date: string }) {
  const lu = useLecture<Donnees>(`/donnees/${table}`, date ? { date } : undefined)
  if (lu.isPending) return <Chargement quoi={`la table ${table}`} />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  const lignes = lu.data.lignes.map((l, _rang) => ({ ...l, _rang }))
  return (
    <DataTable<Ligne>
      libelle={`Table ${table}`}
      lignes={lignes}
      colonnes={colonnes(lu.data)}
      cle={(l) => l._rang}
      placeholder="Chercher dans les lignes chargées…"
      vide="Aucune ligne."
      exporter={{ fichier: `${table}.csv` }}
    />
  )
}

export function DonneesBrutes() {
  const etat = useEtatListe('dq', ['table', 'date'])
  const table = TABLES.find((t) => t === etat.lire('table')) ?? 'matiere'
  const date = etat.lire('date')
  return (
    <Carte titre="Données brutes" serre remplir className={styles.carteListe}>
      <Note>
        Les lignes d’une table telles qu’elles sont en base, pour vérifier un chiffre par un autre chemin.
        Lecture seule ; ni compte, ni session, ni secret, ni journal.
      </Note>
      <div className={styles.marge}>
        <div className={styles.rangee}>
          <ChoixListe
            libelle="Table"
            valeur={table}
            options={TABLES.map((t) => ({ valeur: t, libelle: t }))}
            onChange={(v) => etat.choix.poser('table', v)}
            defaut="matiere"
          />
          <DateChamp
            libelle="Au soir du"
            valeur={date}
            onChange={(v) => etat.choix.poser('date', v || null)}
          />
        </div>
      </div>
      <Tableau table={table} date={date} />
    </Carte>
  )
}
