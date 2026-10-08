/**
 * La coque du bureau (ECRANS-PRO § 2.1 et § 3) : barre latérale du rôle (repliable, tiroir sous
 * 1080 px, refermée à chaque navigation, état replié mémorisé), barre du haut de 56 px (fil
 * d'Ariane, recherche globale, cloche, menu du compte), bandeau du serveur, bandeau d'un écran
 * refusé, et le `<main>` à hauteur bornée que la page remplit (seuls les cadres défilent).
 */
import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router'

import { ROLES_METIER } from '../../lib/droits'
import { useSession } from '../../lib/session'
import type { CleAide } from '../../routes'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import { AideEcran } from './AideEcran'
import { ContexteAide } from './ouvrirAide'
import { BandeauServeur } from './BandeauServeur'
import { BarreLaterale } from './BarreLaterale'
import { Cloche } from './Cloche'
import styles from './Coque.module.css'
import { EcranReserve } from './EcranReserve'
import { useEcranCourant } from './ecranCourant'
import { FilAriane } from './FilAriane'
import { MenuCompte } from './MenuCompte'
import { RechercheGlobale } from './RechercheGlobale'

/** La clé où le poste retient la barre repliée. */
export const CLE_REPLIEE = 'gestion-mp-pro:menu-replie'
/** Sous cette largeur, la barre latérale est un tiroir. */
export const REQUETE_ETROIT = '(max-width: 1079.98px)'

function lireRepliee(): boolean {
  try {
    return window.localStorage.getItem(CLE_REPLIEE) === '1'
  } catch {
    return false
  }
}

/** La barre repliée (au-dessus de 1080 px), retenue par le poste. */
function useRepliee(): [boolean, (v: boolean) => void] {
  const [repliee, setRepliee] = useState(lireRepliee)
  const poser = useCallback((v: boolean) => {
    setRepliee(v)
    try {
      window.localStorage.setItem(CLE_REPLIEE, v ? '1' : '0')
    } catch {
      /* stockage refusé (navigation privée) : l'état vaut pour cette page seulement */
    }
  }, [])
  return [repliee, poser]
}

const etroit = () => typeof window.matchMedia === 'function' && window.matchMedia(REQUETE_ETROIT).matches

export function Coque() {
  const { contexte, role } = useSession()
  const ecran = useEcranCourant()
  const lieu = useLocation()
  const [aide, setAide] = useState<CleAide | null>(null)
  const [tiroir, setTiroir] = useState(false)
  const [repliee, setRepliee] = useRepliee()
  useEffect(() => setTiroir(false), [lieu.pathname])
  const ouvrirAide = useCallback((cle?: CleAide) => setAide(cle ?? ecran?.aide ?? 'aide'), [ecran])
  const basculer = () => (etroit() ? setTiroir((t) => !t) : setRepliee(!repliee))
  const menuVisible = etroit() ? tiroir : !repliee
  return (
    <ContexteAide.Provider value={ouvrirAide}>
      <div className={classes(styles.coque, repliee && styles.sansBarre)}>
        <BarreLaterale
          role={role}
          societe={contexte.societe}
          compteurs={contexte.compteurs}
          actif={ecran ? (ecran.parent ?? ecran.chemin) : null}
          ouverte={tiroir}
          repliee={repliee}
          onFermer={() => setTiroir(false)}
        />
        <div className={styles.colonne}>
          <header className={styles.haut}>
            <button
              type="button"
              className={styles.menu}
              aria-label={menuVisible ? 'Masquer le menu' : 'Afficher le menu'}
              title={menuVisible ? 'Masquer le menu' : 'Afficher le menu'}
              aria-expanded={menuVisible}
              onClick={basculer}
            >
              <Icone nom="menu" taille={20} />
            </button>
            <FilAriane ecran={ecran} />
            <div className={styles.outils}>
              {ROLES_METIER.includes(role) ? <RechercheGlobale role={role} /> : null}
              <Cloche role={role} />
              <MenuCompte />
            </div>
          </header>
          <BandeauServeur alerte={contexte.alerte_serveur} role={role} baseEssai={contexte.base_essai} />
          <EcranReserve key={lieu.key} etat={lieu.state} />
          <main className={styles.contenu}>
            <Outlet />
          </main>
        </div>
      </div>
      {aide ? <AideEcran cle={aide} role={role} onFermer={() => setAide(null)} /> : null}
    </ContexteAide.Provider>
  )
}
