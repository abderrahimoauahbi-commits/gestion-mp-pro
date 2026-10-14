/**
 * Les deux encarts de contrôle de l'onglet Frais (ECRANS-PRO 5.9), chiffres du serveur :
 * - Droits de douane : saisis · attendus (taux du code douanier × valeur en douane = achat + fret +
 *   assurance), écart signalé par le serveur (`droits_ecart_mad`, seuils réglés), matières sans code
 *   actif en liens vers leur fiche (pour y poser le code) ; « Proposer les droits ».
 * - TVA à l'importation : saisie (les **postes de nature TVA** seuls, anomalie 5.2 ; les autres
 *   récupérables à part) · attendue (taux réglé × (valeur en douane + droits + TPI)), écart au-delà de l'écart
 *   toléré réglé (`toler_tva_import`). Les taux sont ceux des réglages, jamais écrits en dur.
 */
import { Link } from 'react-router'

import { Bouton } from '../../composants/saisie/Bouton'
import { classes } from '../../composants/mise-en-page/classes'
import { montantPrecis, nombreSigne, part, VIDE } from '../../lib/format'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'

const seuil = 0.005

function Droits({ d, proposer }: { d: DossierFiche; proposer: (() => void) | null }) {
  const ecart = d.droits_ecart_mad
  const sans = [...d.matieres_sans_code, ...d.matieres_code_inactif]
  return (
    <div
      className={classes(styles.controle, ecart != null && styles.ecart)}
      title="Droits attendus = taux du code douanier de chaque matière × sa valeur en douane (achat + fret + assurance). Le code se porte sur la fiche matière."
    >
      <strong>Droits de douane</strong>
      <span>
        saisis {montantPrecis(d.droits_mad, 'MAD')} · attendus{' '}
        <strong>{d.droits_attendus_mad == null ? VIDE : montantPrecis(d.droits_attendus_mad, 'MAD')}</strong>
      </span>
      {ecart != null ? (
        <span
          className={styles.rouge}
          title="Vérifier la quittance, la valeur déclarée ou le code douanier des matières"
        >
          écart {nombreSigne(ecart, 2)} MAD
        </span>
      ) : null}
      {sans.length ? (
        <span className={styles.note}>
          rien d’attendu : {sans.length} matière(s) sans code actif —{' '}
          {sans.map((m, i) => (
            <span key={m.id}>
              {i ? ', ' : ''}
              <Link to={`/matieres/${m.id}`}>{m.reference}</Link>
              {d.matieres_code_inactif.some((x) => x.id === m.id) ? ' (code désactivé)' : ''}
            </span>
          ))}
        </span>
      ) : null}
      {proposer ? (
        <Bouton
          taille="petit"
          titre="Pré-remplir un frais « Droits de douane » au montant attendu, à vérifier sur la quittance"
          onClick={proposer}
        >
          Proposer les droits
        </Bouton>
      ) : null}
    </div>
  )
}

function Tva({ d }: { d: DossierFiche }) {
  const ecart = d.tva_ecart_mad
  const autres = d.tva_mad - d.tva_saisie_mad
  return (
    <div
      className={classes(styles.controle, ecart != null && styles.ecart)}
      title={`Attendue = ${part(d.taux_tva_import, 0)} (taux réglé) × (valeur en douane + droits + TPI) ; la valeur en douane est achat + fret + assurance, la TPI le frais saisi sinon ${part(d.taux_tpi_import, 2)} de la valeur en douane. Écart toléré : ${part(d.toler_tva_import, 0)} (Réglages › Prix).`}
    >
      <strong>TVA à l’importation</strong>
      <span>
        saisie {montantPrecis(d.tva_saisie_mad, 'MAD')} · attendue{' '}
        <strong
          title={
            d.tva_attendue_mad == null
              ? 'Sans marchandise, pas de valeur en douane : rien n’est attendu'
              : undefined
          }
        >
          {d.tva_attendue_mad == null ? VIDE : montantPrecis(d.tva_attendue_mad, 'MAD')}
        </strong>
      </span>
      {ecart != null ? (
        <span className={styles.rouge} title="Au-delà de l’écart toléré : vérifier la quittance de douane">
          écart {nombreSigne(ecart, 2)} MAD
        </span>
      ) : null}
      {autres > seuil ? (
        <span className={styles.note}>autres récupérables : {montantPrecis(autres, 'MAD')}</span>
      ) : null}
    </div>
  )
}

export function ControlesFrais({ d, proposer }: { d: DossierFiche; proposer: (() => void) | null }) {
  return (
    <div className={styles.controles}>
      <Droits d={d} proposer={proposer} />
      <Tva d={d} />
    </div>
  )
}
