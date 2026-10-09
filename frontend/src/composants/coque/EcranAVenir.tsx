/**
 * La page d'un écran déclaré au registre dont le lot F n'a pas encore livré la page : son titre,
 * son aide, ses onglets permis au rôle (dans l'adresse) et le lot qui la réalise. Le menu, la
 * garde, l'arrivée et la recette peuvent ainsi s'essayer avant les pages.
 */
import { useOngletAdresse } from '../../lib/adresse'
import { AIDE_ECRANS } from '../../lib/aide'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'
import type { Ecran } from '../../routes'
import { EcranAtelier } from '../atelier/EcranAtelier'
import { Carte } from '../mise-en-page/Carte'
import { Onglets } from '../mise-en-page/Onglets'
import { Page } from '../mise-en-page/Page'
import { Vide } from '../retour/Vide'
import { useEcranCourant } from './ecranCourant'
import { EnTete } from './EnTete'
import { TexteAide } from './TexteAide'

function Bureau({ ecran }: { ecran: Ecran }) {
  const { role } = useSession()
  const onglets = ongletsPermis(ecran, role)
  const cles = onglets.map((o) => o.cle)
  const [actif, choisir] = useOngletAdresse(cles, cles[0] ?? '')
  const aide = AIDE_ECRANS[ecran.aide]
  return (
    <Page titre={ecran.titre}>
      <EnTete titre={ecran.titre} sous={aide ? <TexteAide texte={aide.resume} role={role} /> : null} />
      {onglets.length ? <Onglets onglets={onglets} actif={actif} onChange={choisir} /> : null}
      <Carte remplir>
        <Vide>
          Cet écran arrive avec le lot {ecran.lot ?? 'de son domaine'}
          {actif ? ` (onglet « ${onglets.find((o) => o.cle === actif)?.libelle ?? actif} »)` : ''}.
        </Vide>
      </Carte>
    </Page>
  )
}

export default function EcranAVenir() {
  const ecran = useEcranCourant()
  if (!ecran) return null
  if (ecran.atelier) {
    return (
      <EcranAtelier titre={ecran.titre} retour={ecran.chemin === '/atelier' ? false : undefined}>
        <Vide>Cet écran arrive avec le lot {ecran.lot ?? 'de l’atelier'}.</Vide>
      </EcranAtelier>
    )
  }
  return <Bureau ecran={ecran} />
}
