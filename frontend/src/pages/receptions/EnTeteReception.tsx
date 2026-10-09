/**
 * Le haut de la fiche réception (ECRANS-PRO 4.17) : qui, quand, quels bons ; les indicateurs
 * (pesé, écarts, réserve et refus, facture) ; les bandeaux du brouillon (blocages et avertissements
 * du serveur), de l'annulation (motif) et de la validation.
 */
import { Link } from 'react-router'

import { BoutonImprimer } from '../../composants/documents/BoutonImprimer'
import { Indicateurs } from '../../composants/mise-en-page/Indicateurs'
import { Kpi } from '../../composants/retour/Kpi'
import { Note } from '../../composants/retour/Note'
import { formule } from '../../lib/aide'
import { date, horodatage, kg, montant, nombre, part } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import type { Ton } from '../../lib/statuts'
import styles from '../plan-achat/achats.module.css'
import { echeanceLisible, lotsDe, resumerBlocages } from './calculFiche'
import type { ReceptionFiche } from './types'

export function QuiQuand({ r }: { r: ReceptionFiche }) {
  return (
    <span className={styles.rangeeCentree}>
      <span className={styles.note}>
        arrivée du {date(r.date)} · BL {r.numero_bl || '—'}
        {r.commandes.length ? ' · bon(s)' : ' · hors commande'}
      </span>
      {r.commandes.map((c) => (
        <Link key={c.id} to={`/commandes/${c.id}`} title="Ouvrir le bon de commande">
          {c.numero}
        </Link>
      ))}
      <span className={styles.note}>
        · Saisie par {r.cree_par || '—'}
        {r.cree_le ? ` le ${horodatage(r.cree_le)}` : ''}
        {r.controle_par ? ` · contrôlée au quai par ${r.controle_par}` : ''}
        {r.validee_par ? ` · validée par ${r.validee_par} le ${horodatage(r.validee_le)}` : ''}
      </span>
    </span>
  )
}

function detailFacture(r: ReceptionFiche): string {
  const f = r.facture
  if (!f) return 'pas encore reçue'
  const m = f.montant ? montant(f.montant, f.devise) : 'montant non saisi'
  if (f.payee_le) return `${m} · réglée le ${date(f.payee_le)}`
  return `${m} · ${f.echeance ? echeanceLisible(f.echeance) : 'échéance non fixée'}`
}

function tonFacture(r: ReceptionFiche): Ton | undefined {
  const f = r.facture
  if (r.statut === 'validee' && !f) return 'attention'
  if (f?.payee_le) return 'ok'
  return f?.echeance && f.echeance < aujourdhui() ? 'critique' : undefined
}

export function IndicateursReception({ r }: { r: ReceptionFiche }) {
  const tol = r.tolerances?.ecart_pesee ?? 0.02
  const entrees = r.lignes.filter((l) => l.qualite !== 'refuse').length
  const hors = r.lignes.filter((l) => l.hors_tolerance).length
  return (
    <Indicateurs libelle="Indicateurs de la réception">
      <Kpi
        titre="Pesé (entre en stock)"
        valeur={kg(r.pese)}
        formule={formule('reception_pese')}
        detail={`${nombre(entrees)} ligne(s)`}
      />
      <Kpi
        titre="Écarts de pesée"
        valeur={nombre(hors)}
        formule={formule('reception_ecarts')}
        ton={hors ? 'critique' : 'ok'}
        detail={`au-delà de ${part(tol, 0)} de l’annonce`}
      />
      <Kpi
        titre="Sous réserve / refusé"
        valeur={`${nombre(r.nb_reserve)} / ${nombre(r.nb_refus)}`}
        formule={formule('reception_reserve')}
        ton={r.nb_reserve || r.nb_refus ? 'attention' : undefined}
        detail="quarantaine / n’entre pas"
      />
      <Kpi
        titre="Facture"
        valeur={r.facture?.numero ?? '—'}
        formule={formule('reception_facture')}
        ton={tonFacture(r)}
        detail={detailFacture(r)}
      />
    </Indicateurs>
  )
}

function ListeBlocages({ r }: { r: ReceptionFiche }) {
  const resume = resumerBlocages(r.blocages)
  return (
    <Note ton="critique">
      <strong>Avant de valider :</strong>
      <ul className={styles.liste}>
        {resume.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      {resume.length < r.blocages.length ? (
        <details>
          <summary>Le détail, ligne par ligne ({nombre(r.blocages.length)})</summary>
          <ul className={styles.liste}>
            {r.blocages.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </Note>
  )
}

export function BandeauxReception({
  r,
  vientDEtreValidee,
}: {
  r: ReceptionFiche
  vientDEtreValidee: boolean
}) {
  return (
    <>
      {r.statut === 'brouillon' ? (
        <Note>
          Brouillon : rien n’est encore entré en stock, pas encore de numéro. Il se remet à jour tout seul
          (reste à livrer, prix confirmés) si d’autres réceptions passent avant lui.
        </Note>
      ) : null}
      {r.statut === 'brouillon' && r.blocages.length ? <ListeBlocages r={r} /> : null}
      {r.statut === 'brouillon' && r.avertissements.length ? (
        <Note>
          <strong>À savoir avant de valider :</strong>
          <ul className={styles.liste}>
            {r.avertissements.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </Note>
      ) : null}
      {r.statut === 'annulee' ? (
        <Note ton="attention">
          Réception annulée{r.annulation ? ` par ${r.annulation.par} le ${horodatage(r.annulation.le)}` : ''}
          {r.annulation?.motif ? ` — motif : ${r.annulation.motif}` : ''}. Ses entrées en stock ont été
          contre-passées ; les bons concernés attendent de nouveau leur marchandise.
        </Note>
      ) : null}
      {vientDEtreValidee && r.statut === 'validee' ? (
        <Note ton="ok">
          Réception validée sous le n° {r.numero} : {nombre(r.lots.length)} lot(s) créé(s) ou complété(s), la
          marchandise est en stock.{' '}
          {r.lots.length ? (
            <BoutonImprimer
              route="/documents/etiquettes"
              parametres={{ lots: lotsDe(r) }}
              libelle="Imprimer les étiquettes QR à coller sur les palettes"
            />
          ) : null}
        </Note>
      ) : null}
    </>
  )
}
