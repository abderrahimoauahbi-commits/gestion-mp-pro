/**
 * Réceptions › Brouillons · Validées · Annulées (ECRANS-PRO 4.15) : la liste est **paginée au
 * serveur** (recherche, filtres liés et pied de totaux poussés en SQL ; mêmes chiffres qu'avant).
 * Une ligne ouvre la fiche, « Corriger » rouvre la saisie d'un brouillon.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Erreur } from '../../composants/retour/Erreur'
import { useListePaginee } from '../../composants/tableaux/ChargerPlus'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import { kg } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import styles from '../plan-achat/achats.module.css'
import { colonnesReceptions, filtresReceptions } from './colonnesReceptions'
import type { PageReceptions, ReceptionResume } from './types'

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

/** Les paramètres de la route 167 : l'onglet, la recherche et les filtres liés (codes). */
function parametres(statut: StatutListe, etat: EtatTable) {
  const choix = etat.choix.valeurs
  return {
    statut,
    q: etat.recherche.valeur.trim() || undefined,
    fournisseur: choix.fournisseur || undefined,
    origine: choix.origine || undefined,
    facture: choix.facture || undefined,
    qualite: choix.qualite || undefined,
  }
}

/** Le pied de totaux du serveur : le pesé de **tout** l'onglet filtré, aligné sous sa colonne. */
function PiedServeur({ colonnes, pese }: { colonnes: Colonne<ReceptionResume>[]; pese: number }) {
  const visibles = colonnes.filter((c) => !c.cache)
  return (
    <tr>
      {visibles.map((c, i) => (
        <td key={c.cle} style={c.droite ? { textAlign: 'right' } : undefined}>
          {c.total ? kg(pese) : i === 0 ? 'Total' : ''}
        </td>
      ))}
    </tr>
  )
}

export function OngletReceptions({
  statut,
  fournisseurs,
  etat,
  onOuvrir,
  onCorriger,
}: {
  statut: StatutListe
  /** Les fournisseurs du filtre lié, donnés par l'aperçu du serveur (toute la liste). */
  fournisseurs: readonly { id: number; nom: string }[]
  etat: EtatTable
  onOuvrir: (r: ReceptionResume) => void
  onCorriger: (r: ReceptionResume) => void
}) {
  const params = parametres(statut, etat)
  const liste = useListePaginee<ReceptionResume>('/receptions', params)
  const pied = useLecture<PageReceptions>('/receptions', { ...params, limite: 1 })
  const colonnes = useMemo(() => colonnesReceptions(onCorriger), [onCorriger])
  const filtres = useMemo(() => filtresReceptions(fournisseurs), [fournisseurs])
  const carte = CARTES[statut]
  if (liste.requete.isError)
    return <Erreur erreur={liste.requete.error} onReessayer={() => void liste.requete.refetch()} />
  return (
    <Carte titre={<span title={carte.aide}>{carte.titre}</span>} serre remplir className={styles.carteListe}>
      <DataTable<ReceptionResume>
        libelle={`Réceptions — ${carte.titre}`}
        serveur
        lignes={liste.lignes}
        total={liste.total}
        chargerPlus={liste.chargerPlus}
        colonnes={colonnes}
        filtres={filtres}
        cle={(r) => r.id}
        recherche={etat.recherche}
        choix={etat.choix}
        pied={
          liste.lignes.length ? (
            <PiedServeur colonnes={colonnes} pese={pied.data?.pese_total ?? 0} />
          ) : undefined
        }
        placeholder="N°, fournisseur, BL, facture, bon, lot…"
        cliquable={onOuvrir}
        exporter={{ route: '/export/receptions', parametres: { statut } }}
        vide={
          liste.requete.isPending
            ? 'Chargement…'
            : etat.recherche.valeur.trim()
              ? 'Aucune réception de cet onglet ne correspond (voir les autres onglets).'
              : carte.vide
        }
      />
    </Carte>
  )
}
