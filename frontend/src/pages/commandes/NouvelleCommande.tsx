/**
 * Nouvelle commande — chez quel fournisseur ? (`/commandes/nouvelle`, ECRANS-PRO 4.6) : la table
 * des fournisseurs du plan d'achat ; la préparation s'ouvre en pile (`?fournisseur=ID`) avec les
 * quantités que le calcul suggère : on ne commande jamais sans arbitrer.
 */
import { useMemo, useState } from 'react'

import { Fenetre } from '../../composants/mise-en-page/Fenetre'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Interrupteur } from '../../composants/saisie/Interrupteur'
import styles from '../plan-achat/achats.module.css'
import { DataTable } from '../../composants/tableaux/DataTable'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { colonnesFournisseurs } from '../plan-achat/colonnesFournisseurs'
import { usePlanAchat } from '../plan-achat/donnees'
import type { GroupeFournisseur } from '../plan-achat/types'

type Fournisseur = Schema<'FournisseurFiche'> | Schema<'FournisseurResume'>

/** Un fournisseur actif chez qui le calcul ne propose rien : une ligne à zéro. */
function sansPlan(f: Fournisseur): GroupeFournisseur {
  const complet = 'delai_jours' in f
  return {
    fournisseur_id: f.id,
    fournisseur: f.nom,
    pays: f.pays ?? '',
    devise_par_defaut: complet ? f.devise : 'MAD',
    devises: [],
    delai_jours: complet ? f.delai_jours : 0,
    contact: complet ? f.contact : '',
    nb_references: 0,
    quantite: 0,
    montants_par_devise: {},
    montant_mad: 0,
    part_budget: 0,
    urgence: '—',
    ruptures: 0,
    critiques: 0,
    urgents: 0,
  }
}

/** Ceux du plan (budget décroissant, puis nom), et, sur demande, les autres fournisseurs actifs. */
export function fournisseursAProposer(
  plan: readonly GroupeFournisseur[],
  actifs: readonly Fournisseur[],
  tous: boolean,
): GroupeFournisseur[] {
  const avec = plan.filter((g) => g.fournisseur_id != null && g.nb_references > 0)
  const ids = new Set(avec.map((g) => g.fournisseur_id))
  const autres = tous ? actifs.filter((f) => f.actif && !ids.has(f.id)).map(sansPlan) : []
  return [...avec, ...autres].sort(
    (a, b) => b.montant_mad - a.montant_mad || a.fournisseur.localeCompare(b.fournisseur, 'fr'),
  )
}

export function NouvelleCommande({
  onFermer,
  onPreparer,
}: {
  onFermer: () => void
  onPreparer: (fournisseurId: number) => void
}) {
  const plan = usePlanAchat()
  const fournisseurs = useLecture<Fournisseur[]>('/fournisseurs', { actif: true })
  const [tous, setTous] = useState(false)
  const lignes = useMemo(
    () => fournisseursAProposer(plan.data?.fournisseurs ?? [], fournisseurs.data ?? [], tous),
    [plan.data, fournisseurs.data, tous],
  )
  const colonnes = useMemo(
    () => colonnesFournisseurs((g) => g.fournisseur_id && onPreparer(g.fournisseur_id)),
    [onPreparer],
  )
  const erreur = plan.error ?? fournisseurs.error
  return (
    <Fenetre titre="Nouvelle commande — chez quel fournisseur ?" taille="tresLarge" onFermer={onFermer}>
      <Note>
        La préparation s’ouvre avec les quantités que le calcul suggère pour ce fournisseur : vous cochez,
        vous ajustez, et le bon est créé en brouillon. On ne commande jamais sans arbitrer.
      </Note>
      {erreur ? <Erreur erreur={erreur} onReessayer={() => void plan.refetch()} /> : null}
      {!plan.data && !erreur ? <Chargement quoi="les fournisseurs et le plan d’achat" /> : null}
      {plan.data ? (
        <div className={styles.tableFenetre}>
          <DataTable<GroupeFournisseur>
            libelle="Fournisseurs"
            lignes={lignes}
            colonnes={colonnes}
            cle={(g) => g.fournisseur_id ?? g.fournisseur}
            placeholder="Nom, pays, contact, devise…"
            hauteur="fenetre"
            cliquable={(g) => g.fournisseur_id && onPreparer(g.fournisseur_id)}
            outils={
              <Interrupteur
                valeur={tous}
                onChange={setTous}
                libelle="Montrer aussi les fournisseurs chez qui rien n’est à commander"
              />
            }
            vide="Rien n’est à commander aujourd’hui : cochez la case pour voir tous les fournisseurs."
          />
        </div>
      ) : null}
    </Fenetre>
  )
}
