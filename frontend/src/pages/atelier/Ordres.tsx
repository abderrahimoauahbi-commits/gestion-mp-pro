/**
 * Les ordres de l'atelier (`/atelier/ordres`) : brouillons d'abord, puis du plus récent au plus
 * ancien ; 50 cartes puis « charger les suivants » qui dit combien il en reste (an. 18). Un
 * brouillon s'appelle « Brouillon », sa date en note (an. 6).
 */
import { useState } from 'react'
import { Link } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { classes } from '../../composants/mise-en-page/classes'
import { Badge } from '../../composants/retour/Badge'
import { Vide } from '../../composants/retour/Vide'
import { Bouton } from '../../composants/saisie/Bouton'
import { date, kgTelephone, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { attente } from './briques'
import styles from './atelier.module.css'
import type { OrdreResume } from './types'

export const PAGE_ATELIER = 50

/** Brouillons d'abord, puis la date (et le numéro) du plus récent au plus ancien. */
export function trierOrdres(ordres: readonly OrdreResume[]): OrdreResume[] {
  const rang = (o: OrdreResume) => (o.statut === 'brouillon' ? 0 : 1)
  return [...ordres].sort((a, b) => rang(a) - rang(b) || b.date.localeCompare(a.date) || b.id - a.id)
}

/** « ATL-01 100 m² » ou « hors recette ». */
export const fabrication = (o: OrdreResume) => (o.qualites.length ? o.fabrication : 'hors recette')

/** La quantité d'une carte : sorti net d'un validé, à sortir d'un brouillon. */
export function quantiteCarte(o: OrdreResume): [string, string] {
  if (o.statut === 'valide') return [kgTelephone(o.net), 'sorti net']
  if (o.statut === 'annule') return [kgTelephone(o.total), 'annulé']
  return [kgTelephone(o.total), 'à sortir']
}

export function CarteOrdre({ o, vers }: { o: OrdreResume; vers: string }) {
  const [q, sens] = quantiteCarte(o)
  const brouillon = o.statut === 'brouillon'
  return (
    <Link to={vers} className={classes(styles.carteLien, o.blocages.length > 0 && styles.alerte)}>
      <span className={styles.ligne}>
        <strong>{brouillon ? 'Brouillon' : o.numero}</strong>
        <Badge famille="ordre" valeur={o.statut} />
      </span>
      <span className={styles.ligne}>
        <span className={styles.note}>
          {[date(o.date), fabrication(o), o.metier].filter(Boolean).join(' · ')}
        </span>
        <span className={styles.valeur}>
          {q}
          <br />
          <span className={styles.note}>{sens}</span>
        </span>
      </span>
      {o.blocages[0] ? <span className={styles.raison}>sera refusé : {o.blocages[0]}</span> : null}
      {o.retours.length ? (
        <span className={styles.note}>Retours : {o.retours.map((r) => r.numero).join(', ')}</span>
      ) : null}
    </Link>
  )
}

/** « Charger les suivants (40 sur 120) » : on sait toujours ce qui n'est pas montré. */
export function ChargerSuivants({
  montres,
  total,
  onCharger,
}: {
  montres: number
  total: number
  onCharger: () => void
}) {
  if (montres >= total) return null
  return (
    <Bouton taille="atelier" bloc onClick={onCharger}>
      {`${nombre(montres)} sur ${nombre(total)} — charger les suivants`}
    </Bouton>
  )
}

export default function Ordres() {
  const ordres = useLecture<OrdreResume[]>('/ordres/ouverts')
  const [nb, setNb] = useState(PAGE_ATELIER)
  const enAttente = attente([ordres], 'les ordres')
  const liste = trierOrdres(ordres.data ?? [])
  return (
    <EcranAtelier titre="Ordres" retour="/atelier">
      {enAttente ?? (
        <>
          {!liste.length ? <Vide>Aucune sortie pour l’instant.</Vide> : null}
          <ul className={styles.liste}>
            {liste.slice(0, nb).map((o) => (
              <li key={o.id}>
                <CarteOrdre o={o} vers={`/atelier/ordres/${o.id}`} />
              </li>
            ))}
          </ul>
          <ChargerSuivants
            montres={Math.min(nb, liste.length)}
            total={liste.length}
            onCharger={() => setNb(nb + PAGE_ATELIER)}
          />
        </>
      )}
    </EcranAtelier>
  )
}
