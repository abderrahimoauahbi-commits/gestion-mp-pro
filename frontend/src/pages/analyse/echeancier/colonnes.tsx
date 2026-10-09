/**
 * Les colonnes des vues de l'échéancier : la pièce mène à sa réception ou à son dossier ; un
 * montant non saisi sur la facture est « estimé » (pesée × prix) ; une échéance passée est en
 * rouge ; le dernier geste est « Réglée… » ou « Annuler le règlement ».
 */
import type { ReactNode } from 'react'

import type { Colonne } from '../../../composants/tableaux/colonnes'
import { date, montant, nombre } from '../../../lib/format'
import { permis } from '../../../lib/droits'
import type { Role } from '../../../lib/types'
import styles from '../analyse.module.css'
import type { EcheanceLigne } from '../types'
import { AnnulerReglement, Reglee } from './Reglement'

export type VueEcheancier = 'echeances' | 'mois' | 'a_dater' | 'reglees'

/** La fiche d'où vient la pièce : sa réception, ou son dossier d'importation. */
export function adressePiece(l: EcheanceLigne): string | null {
  if (l.reception_id) return `/receptions/${l.reception_id}`
  if (l.dossier_id) return `/dossiers/${l.dossier_id}`
  return null
}

function Montant({ l }: { l: EcheanceLigne }) {
  return (
    <>
      {montant(l.montant, l.devise)}
      {l.estime ? (
        <span
          className={styles.dessous}
          title="Montant non saisi sur la facture : la pesée × le prix de ses réceptions"
        >
          estimé
        </span>
      ) : null}
    </>
  )
}

function communes(role: Role): Colonne<EcheanceLigne>[] {
  return [
    { cle: 'genre', titre: 'Nature' },
    { cle: 'tiers', titre: 'Fournisseur ou prestataire' },
    {
      cle: 'piece',
      titre: 'Pièce',
      lien: (l) => {
        const a = adressePiece(l)
        return a && permis(role, a) ? a : null
      },
    },
    {
      cle: 'montant',
      titre: 'Montant',
      droite: true,
      unite: (l) => l.devise,
      total: true,
      rendu: (l) => <Montant l={l} />,
    },
    {
      cle: 'montant_mad',
      titre: 'Montant MAD',
      droite: true,
      unite: 'MAD',
      total: true,
      rendu: (l) => nombre(l.montant_mad),
    },
  ]
}

const geste = (rendu: (l: EcheanceLigne) => ReactNode): Colonne<EcheanceLigne> => ({
  cle: 'geste',
  titre: '',
  triable: false,
  exporte: false,
  rendu,
})

export function colonnesEcheances(
  vue: VueEcheancier,
  role: Role,
  direction: boolean,
): Colonne<EcheanceLigne>[] {
  if (vue === 'reglees') {
    return [
      { cle: 'payee_le', titre: 'Réglée le', rendu: (l) => date(l.payee_le) },
      { cle: 'date', titre: 'Échéance', rendu: (l) => date(l.date) },
      ...communes(role),
      geste((l) => <AnnulerReglement ligne={l} direction={direction} />),
    ]
  }
  if (vue === 'a_dater') return [...communes(role), geste((l) => <Reglee ligne={l} />)]
  return [
    {
      cle: 'date',
      titre: 'Échéance',
      rendu: (l) => (
        <span className={l.en_retard ? styles.retard : undefined}>
          {date(l.date)}
          {l.en_retard ? <span className={styles.dessous}>en retard</span> : null}
        </span>
      ),
    },
    ...communes(role),
    geste((l) => <Reglee ligne={l} />),
  ]
}
