/**
 * Plan d'achat › Par fournisseur (ECRANS-PRO 4.2) : les fournisseurs à solliciter, le plus gros
 * budget d'abord ; filtres liés (urgence, devise, pays) ; une ligne ouvre la préparation.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { EtatTable } from '../../composants/tableaux/etatAdresse'
import styles from './achats.module.css'
import { colonnesFournisseurs, FILTRES_FOURNISSEURS } from './colonnesFournisseurs'
import type { GroupeFournisseur } from './types'

export function OngletFournisseurs({
  fournisseurs,
  etat,
  onPreparer,
}: {
  fournisseurs: readonly GroupeFournisseur[]
  etat: EtatTable
  onPreparer: (fournisseurId: number) => void
}) {
  const colonnes = useMemo(
    () => colonnesFournisseurs((g) => g.fournisseur_id && onPreparer(g.fournisseur_id)),
    [onPreparer],
  )
  return (
    <Carte
      titre="Fournisseurs à solliciter, le plus gros budget d’abord"
      serre
      remplir
      className={styles.carteListe}
    >
      <DataTable<GroupeFournisseur>
        libelle="Fournisseurs à solliciter"
        lignes={fournisseurs}
        colonnes={colonnes}
        filtres={FILTRES_FOURNISSEURS}
        cle={(g) => g.fournisseur_id ?? g.fournisseur}
        recherche={etat.recherche}
        choix={etat.choix}
        placeholder="Fournisseur, pays, devise…"
        cliquable={(g) => g.fournisseur_id && onPreparer(g.fournisseur_id)}
        exporter={{ route: '/export/plan-achat', parametres: { onglet: 'fournisseurs' } }}
        vide="Rien à commander aujourd’hui."
      />
    </Carte>
  )
}
