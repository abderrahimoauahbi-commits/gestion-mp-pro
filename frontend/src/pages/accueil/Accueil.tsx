/**
 * Ma journée (`/accueil`) : l'accueil des achats et de l'alimentation au bureau (la direction a
 * le Cockpit). Achats : indicateurs, « À faire », « À valider », arrivées de la semaine.
 * Alimentation au bureau : les gestes du jour en tuiles et ses brouillons à valider — ni prix, ni
 * indicateur, ni conseil d'achat (E-01, H-03). La fenêtre d'un besoin signalé s'ouvre par
 * l'adresse (`?signalement=ID`).
 */
import { Tuile, Tuiles } from '../../composants/atelier/Tuile'
import { EnTete } from '../../composants/coque/EnTete'
import { Page } from '../../composants/mise-en-page/Page'
import { nombre } from '../../lib/format'
import { useSession } from '../../lib/session'
import styles from './accueil.module.css'
import { BesoinSignale } from './BesoinSignale'
import { CarteAValider } from './CartesJournee'
import { useBrouillons } from './donnees'
import { JourneeAchats } from './JourneeAchats'
import { brouillonsVisibles } from './taches'

function JourneeAlimentation() {
  const { role } = useSession()
  const brouillons = useBrouillons()
  const ordres = brouillonsVisibles(role, brouillons.data).filter((b) => b.genre === 'ordre').length
  return (
    <div className={`${styles.grille} ${styles.deux}`}>
      <div className={styles.tuilesBureau}>
        <Tuiles>
          <Tuile
            titre="Envoyer aux machines"
            icone="envoyer"
            vers="/ordres/nouveau"
            ton="accent"
            detail="Qualité et m² : les fils et les lots sont proposés."
          />
          <Tuile
            titre="Retour des machines"
            icone="retour"
            vers="/sorties?onglet=valide"
            detail="Choisir l’ordre, puis « Faire un retour »."
          />
          <Tuile
            titre="Les ordres"
            icone="document"
            vers="/sorties"
            ton={ordres ? 'attention' : undefined}
            detail={ordres ? `${nombre(ordres)} brouillon(s) à finir` : 'Validés, brouillons, annulés.'}
          />
          <Tuile
            titre="Métiers à tisser"
            icone="usine"
            vers="/metiers"
            detail="Les fils montés, étage par étage."
          />
          <Tuile
            titre="Déplacer un lot"
            icone="lots"
            vers="/operations/nouvelle?type=transfert"
            detail="D’un magasin à un autre."
          />
        </Tuiles>
      </div>
      <CarteAValider brouillons={brouillons} />
    </div>
  )
}

export default function Accueil() {
  const { moi, role } = useSession()
  const achats = role !== 'alimentation'
  return (
    <Page titre="Ma journée">
      <EnTete
        titre="Ma journée"
        sous={
          achats
            ? `Bonjour ${moi.nom} — ce qui attend une action aujourd’hui.`
            : `Bonjour ${moi.nom} — alimentation des machines`
        }
      />
      {achats ? <JourneeAchats /> : <JourneeAlimentation />}
      {achats ? <BesoinSignale /> : null}
    </Page>
  )
}
