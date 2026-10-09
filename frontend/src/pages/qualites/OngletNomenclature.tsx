/**
 * Onglet « Nomenclature : chaque matière de chaque qualité » (`/qualites?onglet=nomenclature`) :
 * dans l'ordre du moteur, la part, les kg/m² (et ml/m² d'un rôle au mètre), le prix d'achat et
 * le coût au m² (absents pour l'alimentation). La note compte sur la même base que les
 * indicateurs : les qualités en service, les arrêtées à part (P7-27). Une ligne ouvre sa qualité
 * en gardant l'onglet.
 */
import { useMemo } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { formule } from '../../lib/aide'
import { nombre, prix, prixUnite, VIDE } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import { deux } from '../catalogue/colonnesMatieres'
import { useEtatListe } from '../catalogue/etatListe'
import { useNomenclature } from './donnees'
import type { ControleNomenclature, LigneRecette, Nomenclature } from './types'

/** « 312 ligne(s) · recettes à corriger : A, B (arrêtées : C) » ou « · toutes les recettes sont justes ». */
export function noteNomenclature(n: Nomenclature): string {
  const fautes = (actif: boolean) =>
    n.controle.filter((c: ControleNomenclature) => c.actif === actif && !c.conforme).map((c) => c.qualite)
  const actives = fautes(true)
  const arretees = fautes(false)
  const suite = actives.length
    ? ` · recettes à corriger : ${actives.join(', ')}`
    : ' · toutes les recettes sont justes'
  return `${nombre(n.lignes.length)} ligne(s)${suite}${arretees.length ? ` (arrêtées : ${arretees.join(', ')})` : ''}`
}

function PrixAchat({ l }: { l: LigneRecette }) {
  if (!l.prix || !l.devise_prix) return <>{VIDE}</>
  const unite = l.unite_prix ?? 'kg'
  const auKg =
    unite === 'ml' && l.prix_kg
      ? `soit ${prixUnite(l.prix_kg, l.devise_prix, 'kg')} par la densité`
      : undefined
  return <span title={auKg}>{prixUnite(l.prix, l.devise_prix, unite)}</span>
}

function colonnes(fautives: ReadonlySet<string>, voitPrix: boolean): Colonne<LigneRecette>[] {
  const base: Colonne<LigneRecette>[] = [
    {
      cle: 'qualite',
      titre: 'Qualité',
      rendu: (l) =>
        deux(
          <span className={styles.code}>{l.qualite}</span>,
          fautives.has(l.qualite) ? <span className={styles.faux}>recette à corriger</span> : null,
        ),
    },
    { cle: 'role', titre: 'Rôle', valeur: (l) => l.role || 'matière inconnue' },
    {
      cle: 'reference',
      titre: 'Référence',
      rendu: (l) =>
        deux(
          <span className={styles.code}>{l.reference}</span>,
          [l.nature, l.designation].filter(Boolean).join(' · '),
        ),
      recherche: (l) => [l.nature, l.designation],
    },
    { cle: 'fournisseur', titre: 'Fournisseur' },
    { cle: 'pourcentage', titre: 'Part (%)', droite: true, rendu: (l) => nombre(l.pourcentage, 2) },
    {
      cle: 'kg_m2',
      titre: 'kg / m²',
      droite: true,
      rendu: (l) => deux(nombre(l.kg_m2, 4), l.ml_m2 != null ? `${nombre(l.ml_m2, 4)} ml / m²` : null),
    },
  ]
  if (!voitPrix) return base
  return [
    ...base,
    {
      cle: 'prix',
      titre: 'Prix d’achat',
      droite: true,
      valeur: (l) => l.prix_kg,
      rendu: (l) => <PrixAchat l={l} />,
    },
    {
      cle: 'cout_m2_mad',
      titre: 'Coût',
      aide: 'MAD par m², perte matière comprise',
      droite: true,
      rendu: (l) => (l.cout_m2_mad == null ? VIDE : prix(l.cout_m2_mad)),
    },
  ]
}

export function OngletNomenclature({
  voitPrix,
  onOuvrir,
}: {
  voitPrix: boolean
  onOuvrir: (id: number) => void
}) {
  const lu = useNomenclature()
  const etat = useEtatListe('nq', [])
  const fautives = useMemo(
    () => new Set((lu.data?.controle ?? []).filter((c) => !c.conforme).map((c) => c.qualite)),
    [lu.data],
  )
  const cols = useMemo(() => colonnes(fautives, voitPrix), [fautives, voitPrix])
  return (
    <Carte
      titre="Nomenclature : chaque matière de chaque qualité"
      serre
      remplir
      className={styles.carteListe}
    >
      {lu.isPending ? <Chargement quoi="la nomenclature" /> : null}
      {lu.isError ? <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} /> : null}
      {lu.data ? (
        <>
          <Note uneLigne={formule('cout_m2_recette')}>{noteNomenclature(lu.data)}</Note>
          <DataTable<LigneRecette>
            libelle="Nomenclature"
            lignes={lu.data.lignes}
            colonnes={cols}
            cle={(l) => `${l.qualite}|${l.reference}`}
            recherche={etat.recherche}
            choix={etat.choix}
            placeholder="Qualité, matière, rôle, fournisseur…"
            cliquable={(l) => (l.qualite_id != null ? onOuvrir(l.qualite_id) : undefined)}
            vide={lu.data.lignes.length ? 'Rien ne correspond.' : 'Aucune recette saisie.'}
          />
        </>
      ) : null}
    </Carte>
  )
}
