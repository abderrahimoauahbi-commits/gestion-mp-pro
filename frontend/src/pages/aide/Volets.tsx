/** Les sept volets du Mode d'emploi, chacun tiré de `aide.json` (`mode_emploi.<volet>`). */
import type { ComponentType } from 'react'

import { LienAide, TexteAide } from '../../composants/coque/TexteAide'
import { classes } from '../../composants/mise-en-page/classes'
import { developper, FORMULES, MODE_EMPLOI, type Procedure } from '../../lib/aide'
import { permis } from '../../lib/droits'
import type { Role } from '../../lib/types'
import styles from './ModeEmploi.module.css'

type PropsVolet = { role: Role }

function Regles({ role }: PropsVolet) {
  return (
    <ol className={styles.liste}>
      {MODE_EMPLOI.regles.elements.map((r) => (
        <li key={r.titre}>
          <strong>{r.titre}</strong> <TexteAide texte={r.texte} role={role} />
        </li>
      ))}
    </ol>
  )
}

function Roles({ role }: PropsVolet) {
  return (
    <div className={styles.cartes}>
      {MODE_EMPLOI.roles.cartes.map((c) => (
        <section key={c.titre} className={classes(styles.carte, c.role === role && styles.carteMoi)}>
          <h3>
            {c.titre}
            {c.role === role ? <span className={styles.discret}>votre rôle</span> : null}
          </h3>
          <ul className={styles.liste}>
            {c.points.map((p) => (
              <li key={p}>
                <TexteAide texte={p} role={role} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

/** L'adresse d'une procédure pour ce rôle (le point hebdomadaire : Cockpit ou Ma journée). */
export function versProcedure(p: Procedure, role: Role): string | null {
  const vers = p.vers_par_role ? p.vers_par_role[role] : p.vers
  return vers && permis(role, vers) ? vers : null
}

function Pas({ role }: PropsVolet) {
  return (
    <div className={styles.cartes}>
      {MODE_EMPLOI.pas.procedures.map((p) => {
        const vers = versProcedure(p, role)
        return (
          <section key={p.titre} className={styles.carte}>
            <h3>
              {p.titre}
              {vers ? (
                <LienAide vers={vers} role={role}>
                  Ouvrir →
                </LienAide>
              ) : null}
            </h3>
            <ol className={styles.liste}>
              {p.etapes.map((e) => (
                <li key={e}>
                  <TexteAide texte={e} role={role} />
                </li>
              ))}
            </ol>
          </section>
        )
      })}
    </div>
  )
}

function Calculs({ role }: PropsVolet) {
  return (
    <>
      <table className={styles.tableau}>
        <thead>
          <tr>
            <th>Grandeur</th>
            <th>Comment elle est obtenue</th>
          </tr>
        </thead>
        <tbody>
          {MODE_EMPLOI.calculs.lignes.map((cle) => {
            const f = FORMULES[cle]
            return f ? (
              <tr key={cle}>
                <td className={styles.nom}>{f.grandeur}</td>
                <td>{developper(f.texte)}</td>
              </tr>
            ) : null
          })}
        </tbody>
      </table>
      <p className={styles.note}>
        <TexteAide texte={MODE_EMPLOI.calculs.pied} role={role} />
      </p>
    </>
  )
}

function Analyse({ role }: PropsVolet) {
  const voit = permis(role, '/analyse')
  const a = MODE_EMPLOI.analyse
  return (
    <>
      <p className={styles.note}>{voit ? a.note_permise : a.note_reservee}</p>
      <table className={styles.tableau}>
        <tbody>
          {a.lignes.map((l) => (
            <tr key={l.onglet}>
              <td className={styles.nom}>
                {voit ? (
                  <LienAide vers={`/analyse?onglet=${l.onglet}`} role={role}>
                    {l.nom}
                  </LienAide>
                ) : (
                  l.nom
                )}
              </td>
              <td>{l.texte}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

function Ecrans({ role }: PropsVolet) {
  return (
    <>
      <table className={styles.tableau}>
        <thead>
          <tr>
            <th>Écran de l’ERP Fil</th>
            <th>Dans Gestion MP PRO</th>
            <th>Ce qui a changé</th>
          </tr>
        </thead>
        <tbody>
          {MODE_EMPLOI.ecrans.lignes.map((l) => (
            <tr key={`${l.erp}-${l.vers}`}>
              <td>{l.erp}</td>
              <td>
                <LienAide vers={l.vers} role={role}>
                  {l.ou}
                </LienAide>
              </td>
              <td className={styles.discret}>{l.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className={styles.note}>{MODE_EMPLOI.ecrans.pied}</p>
    </>
  )
}

function Telephone({ role }: PropsVolet) {
  return (
    <ol className={styles.liste}>
      {MODE_EMPLOI.telephone.etapes.map((e) => (
        <li key={e}>
          <TexteAide texte={e} role={role} />
        </li>
      ))}
    </ol>
  )
}

export type CleVolet = 'regles' | 'roles' | 'pas' | 'calculs' | 'analyse' | 'ecrans' | 'telephone'

export const VOLETS: Record<CleVolet, { titre: () => string; Contenu: ComponentType<PropsVolet> }> = {
  regles: { titre: () => MODE_EMPLOI.regles.titre, Contenu: Regles },
  roles: { titre: () => MODE_EMPLOI.roles.titre, Contenu: Roles },
  pas: { titre: () => MODE_EMPLOI.pas.titre, Contenu: Pas },
  calculs: { titre: () => MODE_EMPLOI.calculs.titre, Contenu: Calculs },
  analyse: { titre: () => MODE_EMPLOI.analyse.titre, Contenu: Analyse },
  ecrans: { titre: () => MODE_EMPLOI.ecrans.titre, Contenu: Ecrans },
  telephone: { titre: () => MODE_EMPLOI.telephone.titre, Contenu: Telephone },
}
