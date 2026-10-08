/**
 * La page de démonstration du système de composants (lot E1), **en développement seulement** :
 * Vite la sert à `/src/composants/demonstration/index.html` ; la construction de l'écran ne
 * l'emporte pas (seul `index.html` est une entrée). Un faux serveur répond aux lectures des
 * composants qui en font (pièces jointes, historique, lots disponibles) : aucun serveur requis.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter } from 'react-router'

import { creerClientRequetes } from '../../lib/requetes'
import '../../styles/jetons.css'
import '../../styles/base.css'
import { Demonstration } from './Demonstration'
import { installerFauxServeur } from './fauxServeur'

if (!import.meta.env.DEV) throw new Error('La démonstration des composants ne sert qu’en développement.')
installerFauxServeur()

const racine = document.getElementById('racine')
if (!racine) throw new Error('Élément #racine absent.')

createRoot(racine).render(
  <StrictMode>
    <QueryClientProvider client={creerClientRequetes()}>
      <MemoryRouter initialEntries={['/demonstration']}>
        <Demonstration />
      </MemoryRouter>
    </QueryClientProvider>
  </StrictMode>,
)
