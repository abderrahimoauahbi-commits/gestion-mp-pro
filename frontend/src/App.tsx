/**
 * L'application. Socle (lot E0) : un écran d'attente qui prouve la chaîne complète (styles,
 * requêtes, routeur, heure du serveur). La coque, la session et le registre des écrans
 * (`routes.ts`) arrivent avec le lot E2, qui remplace ce contenu.
 */
import { Route, Routes } from 'react-router'

import { messageErreur } from './lib/api'
import { horodatage } from './lib/format'
import { useLecture } from './lib/requetes'

interface Sante {
  version?: string
  heure?: string
}

function Socle() {
  const sante = useLecture<Sante>('/sante')
  let etat = 'Interrogation du serveur…'
  if (sante.isError) etat = messageErreur(sante.error)
  else if (sante.data) etat = `Serveur joint — version ${sante.data.version ?? 'inconnue'}.`
  return (
    <main className="socle">
      <h1>Gestion MP PRO</h1>
      <p>Matières premières de l’usine de tapis.</p>
      <p className="discret" role="status">
        {etat}
      </p>
      {sante.data?.heure ? (
        <p className="discret">Heure du serveur : {horodatage(sante.data.heure)}</p>
      ) : null}
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<Socle />} />
    </Routes>
  )
}
