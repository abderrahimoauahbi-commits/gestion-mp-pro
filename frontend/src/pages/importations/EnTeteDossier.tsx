/**
 * L'en-tête de la fiche d'un dossier (ECRANS-PRO 5.6) : arrivée, banque, ses factures (leurs numéros ;
 * le détail est dans le bloc « Factures du dossier ») ou les pièces d'un dossier repris, ou « Saisi à
 * la main », observations ;
 * les gestes à place fixe (« Modifier l'en-tête », « Clôturer le dossier » / « Rouvrir pour
 * corriger », « Fermer ») ; le panneau d'en-tête (chaque champ s'enregistre en le quittant) avec
 * « Annuler le dossier » (motif exigé, il garde son numéro).
 */
import { Link } from 'react-router'

import { useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { date, horodatage, montantPrecis, nombre } from '../../lib/format'
import { DateEnregistree, TexteEnregistre } from './champsEnregistres'
import { Cloturer, Rouvrir } from './GestesDossier'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'
import type { EnTeteCorps, GestesDossier } from './useDossier'

/** Les factures (leurs numéros), ou les pièces d'un dossier repris, ou « Saisi à la main ». */
function Facture({ d }: { d: DossierFiche }) {
  const ids = new Map(d.receptions.map((r) => [r.numero, r.id]))
  const recs = (numeros: readonly string[]) =>
    numeros.map((n, i) => (
      <span key={n}>
        {i ? ', ' : ''}
        {ids.get(n) != null ? <Link to={`/receptions/${ids.get(n) ?? ''}`}>{n}</Link> : n}
      </span>
    ))
  if (d.factures.length) {
    return (
      <span>
        {d.factures.length > 1 ? 'Factures ' : 'Facture '}
        {d.factures.map((f, i) => (
          <span key={f.id}>
            {i ? ' · ' : ''}
            <strong>{f.numero}</strong>
          </span>
        ))}
        {d.receptions.length ? <> ({recs(d.receptions.map((r) => r.numero))})</> : null}
      </span>
    )
  }
  if (!d.a_la_main && !d.repris) return <span>Plus aucune facture</span>
  if (d.repris && d.pieces.length) {
    return (
      <span>
        {d.pieces.map((p, i) => (
          <span key={p.facture ?? i}>
            {i ? ' · ' : ''}
            {p.facture ? (
              <>
                Facture <strong>{p.facture}</strong>
              </>
            ) : (
              'sans facture'
            )}{' '}
            ({recs(p.receptions)})
          </span>
        ))}
      </span>
    )
  }
  return <span>Saisi à la main (avant la mise en service)</span>
}

/** Ce qui attendra de nouveau son dossier : « La facture F », « Les factures F, G », « Ses marchandises ». */
function quiAttend(d: DossierFiche): string {
  const numeros = d.factures.map((f) => f.numero)
  if (numeros.length > 1) return `Les factures ${numeros.join(', ')}`
  return numeros.length ? `La facture ${numeros[0] ?? ''}` : 'Ses marchandises'
}

/** La question de l'annulation : ce qu'il advient des factures et des frais. */
function questionAnnulation(d: DossierFiche): string {
  const charges = d.frais.reduce((s, f) => s + f.montant, 0)
  const quoi = quiAttend(d)
  const frais = d.frais.length
    ? ` ${nombre(d.frais.length)} frais saisi(s), ${montantPrecis(charges, 'MAD')}, sortiront du coût — pour les garder, détacher plutôt la réception (onglet Marchandises).`
    : ' Aucun frais n’est saisi.'
  const verbe =
    d.factures.length > 1 ? 'attendront de nouveau leur dossier' : 'attendra de nouveau son dossier'
  return `Annuler le dossier ${d.numero} ? Il garde son numéro. ${quoi} ${verbe}.${frais}`
}

/** « Annuler le dossier » : motif exigé, il garde son numéro (ses factures attendent de nouveau). */
function AnnulerDossier({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  const annuler = async (motif: string) => {
    const charges = d.frais.reduce((s, f) => s + f.montant, 0)
    await g.annuler(motif)
    dire(
      `Dossier ${d.numero} annulé : ${quiAttend(d).toLowerCase()} ${d.factures.length > 1 ? 'attendent' : 'attend'} de nouveau ; ${nombre(d.frais.length)} frais (${montantPrecis(charges, 'MAD')}) sortis du coût.`,
    )
  }
  return (
    <Confirmer
      variante="danger"
      motif="exige"
      question={questionAnnulation(d)}
      oui="Oui, annuler le dossier"
      blocages={d.actions.annuler ? [d.actions.annuler] : []}
      titre={`Annuler le dossier : ses factures attendent de nouveau leur dossier${d.frais.length ? `, ses ${nombre(d.frais.length)} frais sortent du coût` : ''}`}
      onOui={annuler}
    >
      Annuler le dossier
    </Confirmer>
  )
}

function Panneau({ d, g, noter }: { d: DossierFiche; g: GestesDossier; noter: () => void }) {
  const corps = (): EnTeteCorps => ({
    libelle: d.libelle,
    banque: d.banque,
    commentaire: d.commentaire,
    date_arrivee: d.date_arrivee,
  })
  const enregistrer = (modif: Partial<EnTeteCorps>) => async () => {
    await g.enTete({ ...corps(), ...modif })
    noter()
  }
  return (
    <div className={styles.panneau} aria-label="En-tête du dossier">
      <Champ libelle="Libellé" className={styles.large}>
        <TexteEnregistre
          libelle="Libellé"
          valeur={d.libelle}
          max={160}
          placeholder="Conteneur Izmir, camion Globaltex…"
          onEnregistrer={(v) => enregistrer({ libelle: v })()}
        />
      </Champ>
      <Champ libelle="Date d’arrivée" className={styles.moyen}>
        <DateEnregistree
          libelle="Date d’arrivée"
          valeur={d.date_arrivee}
          onEnregistrer={(v) => enregistrer({ date_arrivee: v })()}
        />
      </Champ>
      <Champ libelle="Banque" className={styles.etroit}>
        <TexteEnregistre
          libelle="Banque"
          valeur={d.banque}
          max={32}
          placeholder="AWB, BMCI…"
          onEnregistrer={(v) => enregistrer({ banque: v })()}
        />
      </Champ>
      <Champ libelle="Observations" aide="transitaire, n° de DUM…" className={styles.large}>
        <TexteEnregistre
          libelle="Observations"
          valeur={d.commentaire}
          max={2000}
          onEnregistrer={(v) => enregistrer({ commentaire: v })()}
        />
      </Champ>
      <AnnulerDossier d={d} g={g} />
    </div>
  )
}

export interface EnTeteDossierProps {
  d: DossierFiche
  g: GestesDossier
  panneau: boolean
  basculerPanneau: () => void
  enregistreA: string | null
  noter: () => void
}

export function EnTeteDossier({ d, g, panneau, basculerPanneau, enregistreA, noter }: EnTeteDossierProps) {
  const fermer = useFermerFenetre()
  return (
    <>
      <div className={styles.entete}>
        <span>
          Arrivée le <strong>{date(d.date_arrivee)}</strong>
        </span>
        {d.banque ? <span>Banque : {d.banque}</span> : null}
        <Facture d={d} />
        {d.commentaire ? <span title="Observations">« {d.commentaire} »</span> : null}
        {d.statut === 'annule' ? (
          <span className={styles.rouge}>
            Annulé le {horodatage(d.annule_le)}
            {d.annule_par ? ` par ${d.annule_par}` : ''} : {d.annulation_motif}
          </span>
        ) : null}
        <span className={styles.gestes}>
          {enregistreA ? <span className={styles.enregistre}>Enregistré à {enregistreA}</span> : null}
          {d.statut === 'ouvert' ? (
            <Bouton
              taille="petit"
              onClick={basculerPanneau}
              blocages={d.actions.modifier ? [d.actions.modifier] : []}
              titre="Libellé, date d’arrivée, banque, observations — et annuler le dossier"
            >
              {panneau ? 'Terminé' : 'Modifier l’en-tête'}
            </Bouton>
          ) : null}
          {d.statut === 'ouvert' ? <Cloturer d={d} g={g} /> : null}
          {d.statut === 'clos' ? <Rouvrir d={d} g={g} /> : null}
          <Bouton taille="petit" onClick={fermer}>
            Fermer
          </Bouton>
        </span>
      </div>
      {panneau && d.statut === 'ouvert' ? <Panneau d={d} g={g} noter={noter} /> : null}
    </>
  )
}
