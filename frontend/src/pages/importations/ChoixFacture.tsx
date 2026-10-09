/**
 * Choisir une facture (ECRANS-PRO 5.4 ; trois usages : En attente, Nouveau dossier, Second camion) :
 * fournisseur en filtre lié (ses comptes suivent le numéro tapé), numéro tapé qui réduit la liste
 * à la frappe (« FA-2026/117 » = « fa 2026 117 » = « fa2026117 » ; ou des mots de ses réceptions et
 * familles), « Effacer les filtres », et sur chaque facture le geste de l'usage. Un fournisseur
 * marocain sans dossier se confirme sur la ligne (le serveur le refuse sans cette confirmation).
 */
import type { ReactNode } from 'react'

import { Confirmer } from '../../composants/saisie/Confirmer'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import type { Filtre } from '../../composants/tableaux/filtrage'
import { Vide } from '../../composants/retour/Vide'
import { date, kg, nombre } from '../../lib/format'
import styles from './Importations.module.css'
import type { FactureARattacher } from './types'

/** « FA-2026/117 » et « fa 2026 117 » sont la même facture : on compare sans la ponctuation. */
export const nu = (texte: string) =>
  texte
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')

const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

export interface ChoixFactureProps {
  factures: readonly FactureARattacher[]
  /** Le libellé du geste, facture par facture (« Ouvrir son dossier », « Ajouter au dossier 12/26 »). */
  action: (f: FactureARattacher) => string
  onChoisir: (f: FactureARattacher, localConfirme: boolean) => Promise<unknown>
  /** Ce qui empêche le geste (dossier clos : « le rouvrir d'abord »). */
  blocages?: (f: FactureARattacher) => readonly string[]
  hauteur?: 'page' | 'fenetre'
}

function Geste({ f, p }: { f: FactureARattacher; p: ChoixFactureProps }) {
  const blocages = p.blocages?.(f) ?? []
  if (f.local && !f.dossier_id) {
    return (
      <Confirmer
        question={`${f.fournisseur} est un fournisseur marocain : ni douane, ni fret international. Ouvrir quand même un dossier d’importation ?`}
        oui="Oui, l’ouvrir"
        titre="Un fournisseur marocain n’a normalement pas de dossier d’importation"
        taille="petit"
        blocages={blocages}
        onOui={() => p.onChoisir(f, true)}
      >
        {p.action(f)}
      </Confirmer>
    )
  }
  return (
    <Bouton variante="principal" taille="petit" blocages={blocages} onClick={() => p.onChoisir(f, false)}>
      {p.action(f)}
    </Bouton>
  )
}

const FACTURE: Colonne<FactureARattacher> = {
  cle: 'numero',
  titre: 'Facture',
  recherche: (f) => [nu(f.numero), ...f.receptions.map((r) => r.numero)],
  rendu: (f) => (
    <span className={styles.valeur}>
      <strong>{f.numero}</strong>
      <span className={styles.note}>{f.receptions.map((r) => r.numero).join(' · ')}</span>
    </span>
  ),
}

const FOURNISSEUR: Colonne<FactureARattacher> = {
  cle: 'fournisseur',
  titre: 'Fournisseur',
  rendu: (f) => (
    <span className={styles.valeur}>
      <span>{f.fournisseur}</span>
      {f.local ? (
        <span className={styles.note} title="Un fournisseur marocain n’a pas de dossier d’importation">
          fournisseur marocain
        </span>
      ) : null}
    </span>
  ),
}

const RECUE: Colonne<FactureARattacher> = { cle: 'date', titre: 'Reçue le', rendu: (f) => date(f.date) }

const LOTS: Colonne<FactureARattacher> = {
  cle: 'lots',
  titre: 'Lots',
  aide: 'Les lots distincts arrivés par la facture, qui attendent un dossier',
  droite: true,
}

const POIDS: Colonne<FactureARattacher> = {
  cle: 'quantite',
  titre: 'Poids',
  droite: true,
  unite: 'kg',
  rendu: (f) => kg(f.quantite),
}

const VALEURS: Colonne<FactureARattacher> = {
  cle: 'valeurs',
  titre: 'Valeur facture',
  droite: true,
  valeur: (f) => f.valeurs.map((v) => `${v.valeur} ${v.devise}`).join(' '),
  rendu: (f) => (
    <span className={styles.valeur}>
      {f.valeurs.map((v) => (
        <span key={v.devise}>
          {nombre(v.valeur, 2)} {v.devise}
        </span>
      ))}
    </span>
  ),
}

const FAMILLES: Colonne<FactureARattacher> = {
  cle: 'familles',
  titre: 'Familles de fil arrivées',
  valeur: (f) => f.familles.map((x) => x.famille).join(' '),
  rendu: (f) => (
    <span className={styles.valeur}>
      {f.familles.map((x) => (
        <span key={x.famille}>
          {x.famille} · {kg(x.quantite)}
        </span>
      ))}
    </span>
  ),
}

function colonnes(p: ChoixFactureProps): Colonne<FactureARattacher>[] {
  return [
    FACTURE,
    FOURNISSEUR,
    RECUE,
    LOTS,
    POIDS,
    VALEURS,
    FAMILLES,
    {
      cle: 'geste',
      titre: '',
      triable: false,
      exporte: false,
      valeur: () => '',
      rendu: (f) => (
        <span onClick={arreter}>
          <Geste f={f} p={p} />
        </span>
      ),
    },
  ]
}

const FILTRES: readonly Filtre<FactureARattacher>[] = [
  { cle: 'fournisseur', libelle: 'Fournisseur', valeur: (f) => f.fournisseur },
]

export function ChoixFacture(p: ChoixFactureProps): ReactNode {
  if (!p.factures.length) {
    return (
      <Vide>
        Aucune facture n’attend de dossier. Le numéro de facture se saisit sur la réception ; une facture dont
        toute la marchandise est dans son dossier n’apparaît plus ici, ni une réception pas encore validée.
      </Vide>
    )
  }
  return (
    <DataTable
      libelle="Factures qui attendent leur dossier"
      lignes={p.factures}
      colonnes={colonnes(p)}
      cle={(f) => f.facture_id}
      filtres={FILTRES}
      placeholder="Numéro de facture — la liste se réduit à mesure qu’on écrit"
      hauteur={p.hauteur ?? 'page'}
      vide="Aucune facture en attente ne correspond. Vérifier le numéro saisi sur la réception — ou la facture a déjà son dossier."
    />
  )
}
