/**
 * Administration › Téléphone (`/administration?onglet=telephone`, routes 5 et 6) : ouvrir Gestion
 * MP PRO sur un téléphone, dans l'usine (Wi-Fi, QR) ou en dehors (Tailscale). L'adresse des QR se
 * règle dans Administration › Technique ; un appareil perdu se retire dans l'onglet Appareils.
 */
import { Link } from 'react-router'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { useLecture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import styles from './administration.module.css'
import { useQrAcces } from './qr'

type Acces = Schema<'Acces'>

/** Le nom de la machine, sans schéma ni port (« mac-usine »). */
export const nomMachine = (adresse: string | undefined) =>
  (adresse ?? 'serveur-usine').replace(/^https?:\/\//, '').replace(/:\d+$/, '')

function Usine({ a }: { a: Acces }) {
  const qr = useQrAcces().data
  const adresse = a.adresses[0]?.adresse ?? window.location.origin
  return (
    <Carte titre="Dans l’usine, sur le Wi-Fi">
      <p>Adresse de Gestion MP PRO sur le réseau de l’usine :</p>
      <p className={styles.adresse}>{adresse}</p>
      {a.alerte_localhost ? (
        <Note ton="critique">
          {a.alerte_localhost} <Link to="/administration?onglet=technique">Régler l’adresse (Technique)</Link>
        </Note>
      ) : null}
      <div className={styles.rangee}>
        {qr ? <img className={styles.qr} alt={`QR de l’adresse ${a.adresse_qr}`} src={qr} /> : null}
        <span className={styles.note}>
          Visez ce QR avec l’appareil photo du téléphone : Gestion MP PRO s’ouvre à l’adresse {a.adresse_qr}{' '}
          (celle que portent aussi les étiquettes des lots). Pour la changer :{' '}
          <Link to="/administration?onglet=technique">Administration › Technique</Link>.
        </span>
      </div>
      <ol className={styles.liste}>
        <li>Connecter le téléphone au Wi-Fi de l’usine.</li>
        <li>
          Ouvrir le navigateur (Chrome sur Android, Safari sur iPhone) et taper l’adresse ci-dessus :{' '}
          {adresse}.
        </li>
        <li>Choisir son nom et taper son code.</li>
        <li>
          Dans le menu du navigateur, choisir « Ajouter à l’écran d’accueil » : l’écran s’ouvre ensuite d’un
          geste.
        </li>
      </ol>
    </Carte>
  )
}

function Dehors({ a }: { a: Acces }) {
  const machine = nomMachine(a.adresses.find((x) => /machine/i.test(x.libelle))?.adresse)
  const port = /:(\d+)$/.exec(a.adresses[0]?.adresse ?? '')?.[1] ?? '8050'
  return (
    <Carte titre="En dehors de l’usine, en 4G ou 5G">
      <p>
        Hors du Wi-Fi de l’usine, le serveur n’est pas visible d’Internet — c’est voulu. On passe par
        Tailscale, un réseau privé chiffré entre vos appareils.
      </p>
      <ol className={styles.liste}>
        <li>Installer Tailscale sur le serveur et s’y connecter avec un compte (Google, Microsoft…).</li>
        <li>Installer Tailscale sur le téléphone et se connecter avec le même compte.</li>
        <li>{`Relever le nom du serveur dans Tailscale (ici probablement ${machine}).`}</li>
        <li>{`Dans le navigateur du téléphone, taper http://<nom-tailscale-du-serveur>:${port}.`}</li>
        <li>Comme au Wi-Fi : choisir son nom, taper son code, puis « Ajouter à l’écran d’accueil ».</li>
      </ol>
      <Note>
        Tailscale doit rester allumé sur le serveur. Un téléphone perdu se retire dans l’onglet{' '}
        <Link to="/administration?onglet=appareils">Appareils</Link> (et de la console Tailscale) ; son compte
        se désactive dans l’onglet <Link to="/administration?onglet=comptes">Comptes</Link>.
      </Note>
    </Carte>
  )
}

export function Telephone() {
  const lu = useLecture<Acces>('/acces')
  if (lu.isPending) return <Chargement quoi="les adresses d’accès" />
  if (lu.isError) return <Erreur erreur={lu.error} onReessayer={() => void lu.refetch()} />
  return (
    <div className={styles.deux}>
      <Usine a={lu.data} />
      <Dehors a={lu.data} />
    </div>
  )
}
