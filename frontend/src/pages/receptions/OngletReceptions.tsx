/**
 * Réceptions › Brouillons · Validées · Annulées (ECRANS-PRO 4.15) : la recherche porte sur toute la
 * base (le serveur cherche aussi dans les lignes : référence, lot) ; filtres liés ; pied de totaux ;
 * une ligne ouvre la fiche, « Corriger » rouvre la saisie d'un brouillon.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import styles from '../plan-achat/achats.module.css'
import { CHERCHES, colonnesReceptions, filtresReceptions } from './colonnesReceptions'
import type { ReceptionResume } from './types'

export type StatutListe = 'brouillon' | 'validee' | 'annulee'

const CARTES: Record<StatutListe, { titre: string; aide: string; vide: string }> = {
  brouillon: {
    titre: 'Brouillons',
    aide: 'Pas encore entrées en stock ni numérotées : corriger, puis valider',
    vide: 'Aucun brouillon en attente. Un camion arrive ? « Nouvelle réception ».',
  },
  validee: {
    titre: 'Validées',
    aide: 'Entrées en stock : étiquettes, facture, annulation',
    vide: 'Aucune réception ici.',
  },
  annulee: {
    titre: 'Annulées',
    aide: 'Annulées : leurs entrées ont été contre-passées',
    vide: 'Aucune réception ici.',
  },
}

export const CLES_FILTRES_RECEPTIONS = ['fournisseur', 'origine', 'facture', 'qualite'] as const

export function OngletReceptions({
  statut,
  receptions,
  trouvees,
  etat,
  onOuvrir,
  onCorriger,
}: {
  statut: StatutListe
  receptions: readonly ReceptionResume[]
  /** Les id que la recherche du serveur trouve (lignes et lots compris), `null` sans recherche. */
  trouvees: ReadonlySet<number> | null
  etat: EtatTable
  onOuvrir: (r: ReceptionResume) => void
  onCorriger: (r: ReceptionResume) => void
}) {
  const lignes = useMemo(() => receptions.filter((r) => r.statut === statut), [receptions, statut])
  const noms = useMemo(
    () => new Map(receptions.map((r) => [String(r.fournisseur_id), r.fournisseur])),
    [receptions],
  )
  const colonnes = useMemo(() => colonnesReceptions(onCorriger), [onCorriger])
  const q = etat.recherche.valeur
  const carte = CARTES[statut]
  return (
    <Carte titre={<span title={carte.aide}>{carte.titre}</span>} serre remplir className={styles.carteListe}>
      <DataTable<ReceptionResume>
        libelle={`Réceptions — ${carte.titre}`}
        lignes={lignes}
        colonnes={colonnes}
        filtres={filtresReceptions(noms)}
        cle={(r) => r.id}
        recherche={etat.recherche}
        choix={etat.choix}
        rechercheCachee={(r) => [...CHERCHES(r), trouvees?.has(r.id) ? q : '']}
        placeholder="N°, fournisseur, BL, facture, bon, lot…"
        cliquable={onOuvrir}
        exporter={{ route: '/export/receptions', parametres: { statut } }}
        vide={
          q.trim() ? 'Aucune réception de cet onglet ne correspond (voir les autres onglets).' : carte.vide
        }
      />
    </Carte>
  )
}
