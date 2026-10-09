/**
 * Monter les fils (`/atelier/montage`) : le métier (en service), puis l'étage
 * (`?metier=ID`), puis le montage de l'étage (`?metier=ID&etage=N`, `MonterEtage`). Le poids
 * monté se dit « sur les métiers » (an. 7) ; le métier « CODE · Nom » (an. 20).
 */
import { Link, useSearchParams } from 'react-router'

import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { classes } from '../../composants/mise-en-page/classes'
import { Vide } from '../../composants/retour/Vide'
import { kgTelephone, nombre } from '../../lib/format'
import { attente, NoteAtelier } from './briques'
import { nomMetier, useMetiers } from './commun'
import styles from './atelier.module.css'
import { MonterEtage } from './MonterEtage'
import type { MetierFiche } from './types'

/** « 3 étage(s) garni(s) sur 6 · 5 fil(s) · densité à saisir (direction) ». */
export function noteMetier(m: MetierFiche): string {
  const texte = `${nombre(m.etages_garnis)} étage(s) garni(s) sur ${nombre(m.etages)} · ${nombre(m.fils.length)} fil(s)`
  return m.densite_a_saisir ? `${texte} · densité à saisir (direction)` : texte
}

function ChoixMetier() {
  const metiers = useMetiers()
  const actifs = (metiers.data ?? []).filter((m) => m.actif)
  return (
    <EcranAtelier titre="Monter les fils" retour="/atelier">
      {attente([metiers], 'les métiers') ?? (
        <>
          <NoteAtelier>Sur quel métier ?</NoteAtelier>
          {!actifs.length ? <Vide>Aucun métier en service.</Vide> : null}
          <ul className={styles.liste}>
            {actifs.map((m) => (
              <li key={m.id}>
                <Link
                  to={`/atelier/montage?metier=${m.id}`}
                  className={classes(
                    styles.carteLien,
                    (m.etages_trop_larges.length > 0 || m.densite_a_saisir) && styles.alerte,
                  )}
                >
                  <span className={styles.ligne}>
                    <strong>{nomMetier(m)}</strong>
                    <span className={styles.valeur}>{kgTelephone(m.sur_les_metiers)} sur les métiers</span>
                  </span>
                  <span className={styles.note}>{noteMetier(m)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </EcranAtelier>
  )
}

function ChoixEtage({ m }: { m: MetierFiche }) {
  return (
    <EcranAtelier titre={nomMetier(m)} retour="/atelier/montage">
      <NoteAtelier>
        {`Laize ${nombre(m.laize, 2)} m par étage · ${kgTelephone(m.sur_les_metiers)} sur les métiers · ` +
          `${nombre(m.bobines)} bobines. Quel étage ?`}
      </NoteAtelier>
      {m.commentaire ? <NoteAtelier>Observations : {m.commentaire}</NoteAtelier> : null}
      <nav className={styles.grilleEtages} aria-label="Étages">
        {m.etages_detail.map((e) => (
          <Link
            key={e.etage}
            to={`/atelier/montage?metier=${m.id}&etage=${e.etage}`}
            className={classes(styles.etage, e.fils > 0 && styles.garni, e.trop_large && styles.tropLarge)}
          >
            <strong>Étage {e.etage}</strong>
            <span className={styles.note}>
              {e.fils ? `${nombre(e.metres, 2)} / ${nombre(m.laize, 2)} m` : 'vide'}
            </span>
            {e.fils ? (
              <span className={styles.note}>{`${nombre(e.fils)} fil(s) · ${kgTelephone(e.poids)}`}</span>
            ) : null}
          </Link>
        ))}
      </nav>
    </EcranAtelier>
  )
}

export default function Montage() {
  const [params] = useSearchParams()
  const metiers = useMetiers()
  const id = Number(params.get('metier')) || null
  const etage = Number(params.get('etage')) || null
  if (id == null) return <ChoixMetier />
  const m = metiers.data?.find((x) => x.id === id)
  if (!m)
    return (
      <EcranAtelier titre="Monter les fils" retour="/atelier/montage">
        {attente([metiers], 'le métier') ?? <Vide>Ce métier n’existe pas.</Vide>}
      </EcranAtelier>
    )
  if (etage == null || etage < 1 || etage > m.etages) return <ChoixEtage m={m} />
  return <MonterEtage key={`${id}-${etage}`} id={id} etage={etage} />
}
