/** Démarrage de l'écran : styles, client de requêtes, routeur, service worker. */
import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App'
import { creerClientRequetes } from './lib/requetes'
import './styles/jetons.css'
import './styles/base.css'

const client = creerClientRequetes()

/**
 * Le service worker rend l'application installable au téléphone ; il ne garde aucune donnée
 * (`public/sw.js`). Il ne s'enregistre qu'en contexte sûr (HTTPS, ou localhost) et dans l'écran
 * construit : en développement, il gênerait le rechargement à chaud.
 */
function enregistrerServiceWorker(): void {
  if (!import.meta.env.PROD || !window.isSecureContext || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .catch((e: unknown) => console.warn('Service worker refusé :', e))
  })
}

const racine = document.getElementById('racine')
if (!racine) throw new Error('Élément #racine absent de index.html.')

createRoot(racine).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

enregistrerServiceWorker()
