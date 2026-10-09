/**
 * La barre latérale (ECRANS-PRO § 2.1) : le menu du rôle, dérivé du registre (`routes.ts`) — une
 * entrée par écran permis, groupes vides masqués, libellé = titre de la page, détail en infobulle.
 * Pastilles (compteurs de GET /contexte, relus toutes les 3 minutes et après chaque écriture) :
 * Stock = alerte rouge ; Analyse = contrôles à corriger (le lien mène alors aux Contrôles) ;
 * Commandes = bons à approuver (direction) ; Réceptions = brouillons. Le menu tient sans défiler
 * en 1366 × 768.
 */
import { Link } from 'react-router'

import { menuDe } from '../../lib/droits'
import type { CompteursMenu } from '../../lib/types-coque'
import type { Role } from '../../lib/types'
import type { Ecran } from '../../routes'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import { Pastille } from '../retour/Pastille'
import styles from './BarreLaterale.module.css'

interface DefPastille {
  /** Le nom du compteur dans `contexte.compteurs`. */
  cle: string
  roles: readonly Role[]
  titre: string
  /** L'adresse du lien quand la pastille est allumée. */
  lien?: string
}

/** Les pastilles du menu : une définition nommée chacune (P1-9). */
export const PASTILLES: Readonly<Record<string, DefPastille>> = {
  '/stock': {
    cle: 'alerte_rouge',
    roles: ['direction', 'achats', 'alimentation'],
    titre: 'en rupture ou critiques',
  },
  '/commandes': { cle: 'a_approuver', roles: ['direction'], titre: 'bon(s) à approuver' },
  '/receptions': {
    cle: 'receptions_brouillon',
    roles: ['direction', 'achats'],
    titre: 'réception(s) en brouillon',
  },
  '/analyse': {
    cle: 'anomalies',
    roles: ['direction', 'achats'],
    titre: 'contrôle(s) à corriger',
    lien: '/analyse?onglet=controles',
  },
}

/** Le compteur d'une entrée pour ce rôle (0 sans pastille). */
export function compteDe(e: Ecran, role: Role, compteurs: CompteursMenu | undefined): number {
  const p = PASTILLES[e.chemin]
  if (!p || !p.roles.includes(role)) return 0
  return compteurs?.[p.cle] ?? 0
}

function Entree({
  e,
  role,
  compteurs,
  active,
}: {
  e: Ecran
  role: Role
  compteurs?: CompteursMenu
  active: boolean
}) {
  const n = compteDe(e, role, compteurs)
  const p = PASTILLES[e.chemin]
  const vers = n && p?.lien ? p.lien : e.chemin
  const infobulle = n && p ? `${e.detail ?? e.titre} — ${n} ${p.titre}` : (e.detail ?? e.titre)
  return (
    <li>
      <Link
        to={vers}
        className={classes(styles.lien, active && styles.actif)}
        aria-current={active ? 'page' : undefined}
        title={infobulle}
      >
        <span className={styles.libelle}>{e.titre}</span>
        {p ? <Pastille nombre={n} titre={p.titre} /> : null}
      </Link>
    </li>
  )
}

export interface BarreLateraleProps {
  role: Role
  societe?: string
  compteurs?: CompteursMenu
  /** Le chemin de l'entrée active (l'écran, ou la liste sous une fiche). */
  actif: string | null
  /** Au-dessous de 1080 px : tiroir ouvert. */
  ouverte?: boolean
  /** Au-dessus de 1080 px : barre repliée par l'utilisateur. */
  repliee?: boolean
  onFermer?: () => void
}

export function BarreLaterale({
  role,
  societe,
  compteurs,
  actif,
  ouverte,
  repliee,
  onFermer,
}: BarreLateraleProps) {
  const menu = menuDe(role)
  return (
    <>
      {ouverte ? <div className={styles.voile} onMouseDown={onFermer} aria-hidden="true" /> : null}
      <nav
        aria-label="Menu principal"
        className={classes(styles.barre, ouverte && styles.ouverte, repliee && styles.repliee)}
      >
        <div className={styles.marque}>
          <Icone nom="usine" taille={22} />
          <div className={styles.nom}>
            <strong>Gestion MP PRO</strong>
            <span>{societe || 'Matières premières'}</span>
          </div>
        </div>
        <div className={styles.groupes}>
          {menu.map((g) => (
            <section key={g.groupe} className={styles.groupe} aria-label={g.groupe}>
              <h2 className={styles.titreGroupe}>{g.groupe}</h2>
              <ul>
                {g.entrees.map((e) => (
                  <Entree
                    key={e.chemin}
                    e={e}
                    role={role}
                    compteurs={compteurs}
                    active={actif === e.chemin}
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      </nav>
    </>
  )
}
