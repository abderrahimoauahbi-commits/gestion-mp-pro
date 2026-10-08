/**
 * Mon compte (`/compte`, tous les rôles, P1-24) : qui je suis, mon courriel (PUT /moi), mon code
 * (PUT /moi/code, l'ancien exigé, les autres sessions fermées), l'apparence de l'écran, et — pour la
 * direction et l'administrateur — les appareils enrôlés.
 */
import { useState } from 'react'

import { EnTete } from '../../composants/coque/EnTete'
import { useGardeSaisie } from '../../composants/coque/garde'
import { Carte } from '../../composants/mise-en-page/Carte'
import { Definitions } from '../../composants/mise-en-page/Definitions'
import { Grille } from '../../composants/mise-en-page/Grille'
import { Page } from '../../composants/mise-en-page/Page'
import { dire } from '../../composants/retour/Messages'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ, erreurDuChamp } from '../../composants/saisie/Champ'
import { Saisie } from '../../composants/saisie/Saisie'
import { Segments } from '../../composants/saisie/Segments'
import { api } from '../../lib/api'
import { useEcriture } from '../../lib/requetes'
import { useSession } from '../../lib/session'
import type { Moi } from '../../lib/types-provisoires-s2'
import { Appareils } from './Appareils'
import { ChangerCode } from './ChangerCode'
import styles from './MonCompte.module.css'
import { appliquerTheme, lireTheme, type Theme } from './theme'

function Courriel() {
  const { moi, rafraichir } = useSession()
  const [email, setEmail] = useState(moi.email ?? '')
  const ecriture = useEcriture((corps: { email: string; version?: number }) => api.put<Moi>('/moi', corps))
  const change = email.trim() !== (moi.email ?? '')
  useGardeSaisie(change)
  const enregistrer = async () => {
    await ecriture.mutateAsync({ email: email.trim(), version: moi.version })
    await rafraichir()
    dire('Courriel enregistré.')
  }
  return (
    <>
      <Champ
        libelle="Courriel"
        aide="Pour les notifications et le courriel du lundi."
        erreur={erreurDuChamp(ecriture.error, 'email')}
      >
        <Saisie valeur={email} onChange={setEmail} type="email" max={120} autoComplete="email" />
      </Champ>
      <div className={styles.gestes}>
        <Bouton
          variante="principal"
          grise={change ? undefined : 'Rien n’a changé.'}
          attente="Enregistrement…"
          onClick={enregistrer}
        >
          Enregistrer le courriel
        </Bouton>
      </div>
    </>
  )
}

function Apparence() {
  const [theme, setTheme] = useState<Theme>(lireTheme)
  return (
    <Champ libelle="Apparence de l’écran" aide="Pour ce navigateur seulement." groupe>
      <Segments
        valeur={theme}
        onChange={(t) => {
          setTheme(t)
          appliquerTheme(t, true)
        }}
        options={[
          { valeur: 'poste', libelle: 'Selon le poste' },
          { valeur: 'clair', libelle: 'Claire' },
          { valeur: 'sombre', libelle: 'Sombre' },
        ]}
      />
    </Champ>
  )
}

export default function MonCompte() {
  const { moi, role } = useSession()
  const technique = role === 'direction' || role === 'administrateur'
  return (
    <Page titre="Mon compte">
      <EnTete
        titre="Mon compte"
        sous="Qui vous êtes pour Gestion MP PRO, votre code, l’apparence de l’écran."
      />
      <div className={styles.cartes}>
        <Carte titre="Qui je suis">
          <Definitions
            colonnes={1}
            items={[
              ['Nom', moi.nom],
              ['Identifiant', moi.identifiant],
              ['Rôle', moi.role_libelle],
            ]}
          />
          <Courriel />
        </Carte>
        <Carte titre="Changer mon code">
          <ChangerCode />
        </Carte>
        <Carte titre="Écran et appareils">
          <Grille colonnes={1}>
            <Apparence />
          </Grille>
          {technique ? <Appareils /> : null}
        </Carte>
      </div>
    </Page>
  )
}
