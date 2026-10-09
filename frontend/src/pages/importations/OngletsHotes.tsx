/**
 * Les pages Analyse et Réglages appartiennent au lot F8 ; le lot F5 y réalise trois onglets :
 * « Coût de revient » (`/analyse?onglet=revient`), « Postes de frais » et « Codes douaniers »
 * (`/reglages?onglet=postes|codes`). En attendant les pages de F8, ce gabarit provisoire les
 * accueille : en-tête, onglets permis au rôle (dans l'adresse), et pour chaque autre onglet la
 * même phrase que `EcranAVenir`. Le lot F8 remplace `page` dans ses `ecrans.ts` par ses pages et
 * y monte `AnalyseRevient`, `PostesFrais` et `CodesDouaniers` (docs/lots/F5.md) ; ce fichier
 * disparaît alors.
 */
import type { ComponentType } from 'react'

import { useEcranCourant } from '../../composants/coque/ecranCourant'
import { EnTete } from '../../composants/coque/EnTete'
import { TexteAide } from '../../composants/coque/TexteAide'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Onglets } from '../../composants/mise-en-page/Onglets'
import { Page } from '../../composants/mise-en-page/Page'
import { Vide } from '../../composants/retour/Vide'
import { useOngletAdresse } from '../../lib/adresse'
import { AIDE_ECRANS } from '../../lib/aide'
import { ongletsPermis } from '../../lib/droits'
import { useSession } from '../../lib/session'

/** Une page de F8 dont certains onglets sont réalisés ici (`contenus` : clé d'onglet → contenu). */
export function PageHote({ contenus }: { contenus: Readonly<Record<string, ComponentType>> }) {
  const ecran = useEcranCourant()
  const { role } = useSession()
  const onglets = ecran ? ongletsPermis(ecran, role) : []
  const cles = onglets.map((o) => o.cle)
  const [actif, choisir] = useOngletAdresse(cles, cles[0] ?? '')
  if (!ecran) return null
  const Contenu = contenus[actif]
  const aide = AIDE_ECRANS[ecran.aide]
  return (
    <Page titre={ecran.titre}>
      <EnTete titre={ecran.titre} sous={aide ? <TexteAide texte={aide.resume} role={role} /> : null} />
      <Onglets
        libelle={`Onglets de ${ecran.titre}`}
        onglets={onglets.map((o) => ({ cle: o.cle, libelle: o.libelle, court: o.court }))}
        actif={actif}
        onChange={choisir}
      />
      {Contenu ? (
        <Contenu />
      ) : (
        <Carte remplir>
          <Vide>
            Cet écran arrive avec le lot {ecran.lot ?? 'de son domaine'} (onglet «{' '}
            {onglets.find((o) => o.cle === actif)?.libelle ?? actif} »).
          </Vide>
        </Carte>
      )}
    </Page>
  )
}
