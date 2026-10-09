/**
 * Fiche dossier › Échéancier (ECRANS-PRO 5.10) : ce que le dossier engage à payer, mois par mois
 * (« Sans échéance » à la fin), factures de marchandise et frais, dans l'ordre du serveur (échéance
 * puis quoi). Chaque mois dit ce qui reste à payer, devise par devise (jamais additionnées). Une
 * facture dont toute la marchandise a été détachée reste, « marchandise détachée » (anomalie 5.19).
 * Le règlement se saisit dans Analyse › Échéancier.
 */
import { Link } from 'react-router'

import { Badge } from '../../composants/retour/Badge'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { date, mois, montants, montantPrecis, VIDE } from '../../lib/format'
import styles from './Importations.module.css'
import type { DossierFiche, Echeance } from './types'

const arreter = (e: { stopPropagation: () => void }) => e.stopPropagation()

/** Le mois d'une échéance (« 2026-10 ») ou '' sans échéance. */
const moisDe = (e: Echeance) => (e.echeance ? e.echeance.slice(0, 7) : '')

/** Ce qui reste à payer dans un groupe, par devise : « à payer 12 345,00 USD · 3 000,00 MAD ». */
function resteAPayer(lignes: readonly Echeance[]): string {
  const parDevise: Record<string, number> = {}
  for (const e of lignes) {
    if (e.payee_le || e.detachee) continue
    parDevise[e.devise] = (parDevise[e.devise] ?? 0) + e.montant
  }
  return Object.keys(parDevise).length ? `à payer ${montants(parDevise, true)}` : 'tout est réglé'
}

interface LigneGroupe {
  e: Echeance
  rang: number
  /** Sur la première ligne de son mois : le mois et ce qui reste à payer. */
  groupe: { libelle: string; reste: string; sans: boolean } | null
}

function grouper(echeancier: readonly Echeance[]): LigneGroupe[] {
  const ordre = [...echeancier].sort(
    (a, b) => Number(!a.echeance) - Number(!b.echeance) || (a.echeance ?? '').localeCompare(b.echeance ?? ''),
  )
  return ordre.map((e, rang) => {
    const m = moisDe(e)
    const premier = rang === 0 || moisDe(ordre[rang - 1] ?? e) !== m
    const memes = ordre.filter((x) => moisDe(x) === m)
    return {
      e,
      rang,
      groupe: premier
        ? { libelle: m ? mois(m) : 'Sans échéance', reste: resteAPayer(memes), sans: !m }
        : null,
    }
  })
}

const ECHEANCE: Colonne<LigneGroupe> = {
  cle: 'echeance',
  titre: 'Échéance',
  triable: false,
  valeur: (l) => l.e.echeance,
  rendu: (l) => date(l.e.echeance),
}

const NATURE: Colonne<LigneGroupe> = {
  cle: 'nature',
  titre: 'Nature',
  triable: false,
  valeur: (l) => l.e.nature,
  rendu: (l) => <Badge ton={l.e.nature === 'marchandise' ? 'accent' : 'neutre'}>{l.e.nature}</Badge>,
}

const QUOI: Colonne<LigneGroupe> = {
  cle: 'quoi',
  titre: 'Quoi',
  triable: false,
  valeur: (l) => l.e.quoi,
  rendu: (l) => (
    <span className={styles.valeur}>
      <span>{l.e.quoi}</span>
      {l.e.detachee ? <span className={styles.note}>marchandise détachée</span> : null}
    </span>
  ),
}

const TIERS: Colonne<LigneGroupe> = {
  cle: 'tiers',
  titre: 'Tiers',
  triable: false,
  valeur: (l) => l.e.tiers || VIDE,
}

const PIECE: Colonne<LigneGroupe> = {
  cle: 'piece',
  titre: 'Pièce',
  triable: false,
  valeur: (l) => l.e.piece,
  rendu: (l) => (
    <span className={styles.valeur}>
      <span>{l.e.piece || VIDE}</span>
      {l.e.date_piece ? <span className={styles.note}>du {date(l.e.date_piece)}</span> : null}
    </span>
  ),
}

const MONTANT: Colonne<LigneGroupe> = {
  cle: 'montant',
  titre: 'Montant',
  droite: true,
  triable: false,
  valeur: (l) => l.e.montant,
  rendu: (l) => (
    <span className={styles.valeur}>
      <span>{montantPrecis(l.e.montant, l.e.devise)}</span>
      {l.e.estime ? (
        <span
          className={styles.note}
          title="La facture n’a pas de montant saisi : ce que sa marchandise au dossier a apporté, pesée × prix"
        >
          estimé
        </span>
      ) : null}
    </span>
  ),
}

const REGLEMENT: Colonne<LigneGroupe> = {
  cle: 'reglement',
  titre: 'Règlement',
  triable: false,
  valeur: (l) => l.e.payee_le ?? '',
  rendu: (l) =>
    l.e.payee_le ? (
      <Badge ton="ok">réglé le {date(l.e.payee_le)}</Badge>
    ) : l.e.detachee ? (
      VIDE
    ) : (
      <Link
        to={`/analyse?onglet=echeancier&q=${encodeURIComponent(l.e.piece || l.e.quoi)}`}
        onClick={arreter}
      >
        à payer
      </Link>
    ),
}

function colonnes(versFrais: () => void): Colonne<LigneGroupe>[] {
  return [
    {
      cle: 'mois',
      titre: 'Mois',
      triable: false,
      valeur: (l) => l.groupe?.libelle ?? '',
      rendu: (l) =>
        l.groupe ? (
          <span className={styles.valeur}>
            <strong>{l.groupe.libelle}</strong>
            <span className={styles.note}>{l.groupe.reste}</span>
            {l.groupe.sans ? (
              <Bouton taille="petit" variante="fantome" onClick={versFrais}>
                la saisir sur le frais
              </Bouton>
            ) : null}
          </span>
        ) : null,
    },
    ECHEANCE,
    NATURE,
    QUOI,
    TIERS,
    PIECE,
    MONTANT,
    REGLEMENT,
  ]
}

export function VoletEcheancier({ d, versFrais }: { d: DossierFiche; versFrais: () => void }) {
  if (!d.echeancier.length) {
    return <Vide>Ni facture de marchandise, ni frais dans ce dossier : rien à payer encore.</Vide>
  }
  return (
    <DataTable
      libelle="Échéancier du dossier : les devises ne s’additionnent pas"
      lignes={grouper(d.echeancier)}
      colonnes={colonnes(versFrais)}
      cle={(l) => l.rang}
      recherche={false}
      hauteur="fenetre"
    />
  )
}
