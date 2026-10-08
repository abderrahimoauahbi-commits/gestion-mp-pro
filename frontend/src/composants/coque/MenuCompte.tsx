/**
 * Le menu du compte (en-tête, à droite) : le nom et le rôle ; Mon compte, Aide de l'écran,
 * Signaler un besoin (rôles métier), Se déconnecter — **confirmé** sur place, et gardé par la
 * saisie en cours (« Des modifications ne sont pas enregistrées. Les abandonner ? »).
 */
import { useState } from 'react'
import { useNavigate } from 'react-router'

import { ROLES_METIER } from '../../lib/droits'
import { useSession } from '../../lib/session'
import { Icone, type NomIcone } from '../mise-en-page/Icone'
import { Confirmer } from '../saisie/Confirmer'
import { useOuvrirAide } from './ouvrirAide'
import { useFermeDehors } from './Cloche'
import { proteger } from './garde'
import styles from './MenuCompte.module.css'
import { SignalerBesoin } from './SignalerBesoin'

/** Les initiales d'un nom (« Karim BENALI » → « KB »). */
export function initiales(nom: string): string {
  const mots = nom.trim().split(/\s+/).filter(Boolean)
  const lettres = mots.length > 1 ? [mots[0], mots[mots.length - 1]] : mots
  return lettres.map((m) => m?.[0]?.toUpperCase() ?? '').join('') || '?'
}

function Choix({ icone, children, onClick }: { icone: NomIcone; children: string; onClick: () => void }) {
  return (
    <button type="button" className={styles.choix} onClick={onClick}>
      <Icone nom={icone} />
      {children}
    </button>
  )
}

export function MenuCompte() {
  const { moi, role, deconnecter } = useSession()
  const naviguer = useNavigate()
  const ouvrirAide = useOuvrirAide()
  const [ouvert, setOuvert] = useState(false)
  const [signaler, setSignaler] = useState(false)
  const boite = useFermeDehors(ouvert, () => setOuvert(false))
  const puis = (action: () => void) => () => {
    setOuvert(false)
    action()
  }
  return (
    <div className={styles.compte} ref={boite}>
      <button
        type="button"
        className={styles.bouton}
        aria-expanded={ouvert}
        aria-label={`Mon compte : ${moi.nom}, ${moi.role_libelle}`}
        onClick={() => setOuvert((o) => !o)}
      >
        <span className={styles.avatar} aria-hidden="true">
          {initiales(moi.nom)}
        </span>
        <span className={styles.qui}>
          <strong>{moi.nom}</strong>
          <span>{moi.role_libelle}</span>
        </span>
        <Icone nom="chevronBas" />
      </button>
      {ouvert ? (
        <div className={styles.panneau} role="group" aria-label="Mon compte">
          <Choix icone="compte" onClick={puis(() => proteger(() => naviguer('/compte')))}>
            Mon compte
          </Choix>
          {ouvrirAide ? (
            <Choix icone="aide" onClick={puis(() => ouvrirAide())}>
              Aide de l’écran
            </Choix>
          ) : null}
          {ROLES_METIER.includes(role) ? (
            <Choix icone="signaler" onClick={puis(() => setSignaler(true))}>
              Signaler un besoin
            </Choix>
          ) : null}
          <div className={styles.sortie}>
            <Confirmer
              question="Se déconnecter ?"
              oui="Oui, me déconnecter"
              icone="deconnexion"
              onOui={puis(() => proteger(() => void deconnecter()))}
            >
              Se déconnecter
            </Confirmer>
          </div>
        </div>
      ) : null}
      {signaler ? <SignalerBesoin onFermer={() => setSignaler(false)} /> : null}
    </div>
  )
}
