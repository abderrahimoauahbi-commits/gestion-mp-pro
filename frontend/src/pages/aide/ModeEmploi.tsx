/**
 * Le Mode d'emploi (`/aide?onglet=regles|roles|pas|calculs|analyse|ecrans|telephone`, tous les
 * rôles) : sept onglets tirés de `aide.json`, le texte défile dans sa carte (la page ne défile
 * pas), les liens vers un écran que le rôle ne voit pas sont dits sans lien (P1-19).
 */
import { EnTete } from '../../composants/coque/EnTete'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Cadre } from '../../composants/tableaux/Cadre'
import { useOngletAdresse } from '../../lib/adresse'
import { MODE_EMPLOI } from '../../lib/aide'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import { ecranParChemin } from '../../routes'
import styles from './ModeEmploi.module.css'
import { VOLETS, type CleVolet } from './Volets'

const CLES = Object.keys(VOLETS).filter((c): c is CleVolet => c in VOLETS)

export default function ModeEmploi() {
  const { role } = useSession()
  const [volet, choisir] = useOngletAdresse<CleVolet>(CLES, 'regles')
  const ecran = ecranParChemin('/aide')
  const onglets = ecran
    ? ongletsPermis(ecran, role).filter((o): o is typeof o & { cle: CleVolet } => o.cle in VOLETS)
    : []
  const { titre, Contenu } = VOLETS[volet]
  return (
    <Page titre={MODE_EMPLOI.titre}>
      <EnTete titre={MODE_EMPLOI.titre} sous={MODE_EMPLOI.sous_titre} />
      <Onglets onglets={onglets} actif={volet} onChange={choisir} libelle="Volets du Mode d’emploi" />
      <Carte titre={titre()} remplir>
        <Cadre className={styles.texte}>
          <Contenu role={role} />
        </Cadre>
      </Carte>
    </Page>
  )
}
