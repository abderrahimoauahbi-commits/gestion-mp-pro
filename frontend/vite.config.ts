/// <reference types="vitest/config" />
/**
 * Écran de Gestion MP PRO : serveur de développement (port 5196) et essais (vitest).
 *
 * En développement, `/api` est relayé au serveur de Gestion MP PRO (port 8050, ARCHITECTURE § 14.1) ;
 * `GESTIONMPPRO_API` vise un autre serveur (par exemple un poste de recette).
 */
import type { ServerResponse } from 'node:http'

import react from '@vitejs/plugin-react'
import { defineConfig, type ProxyOptions } from 'vite'

const serveur = process.env.GESTIONMPPRO_API ?? 'http://127.0.0.1:8050'

/** Serveur arrêté : une réponse 502 au format des refus, plutôt qu'un « 500 » muet du relais. */
const relais: ProxyOptions = {
  target: serveur,
  configure: (proxy) => {
    proxy.on('error', (_erreur, _requete, reponse) => {
      if (!('writeHead' in reponse)) return
      const r: ServerResponse = reponse
      if (r.headersSent) return
      r.writeHead(502, { 'Content-Type': 'application/json' })
      r.end(
        JSON.stringify({
          detail: `Le serveur de Gestion MP PRO (${serveur}) ne répond pas : démarrez-le.`,
          code: 'serveur_absent',
        }),
      )
    })
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5196,
    strictPort: true,
    proxy: { '/api': relais },
  },
  preview: { port: 5196, strictPort: true, proxy: { '/api': relais } },
  build: { outDir: 'dist', sourcemap: true },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/preparation-essais.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: { modules: { classNameStrategy: 'non-scoped' } },
    restoreMocks: true,
    unstubGlobals: true,
  },
})
