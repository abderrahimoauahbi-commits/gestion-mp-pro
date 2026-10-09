/**
 * Un QR du serveur (SVG de segno, avec son espace de noms `xmlns` depuis RESTES3) en image : une
 * adresse `data:` que la balise `<img>` affiche telle quelle.
 */
import { useQuery } from '@tanstack/react-query'

import { adresseApi } from '../../lib/api'

/** L'adresse `data:` d'un SVG, tel que le serveur le rend. */
export function svgEnImage(svg: string): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

/** Le QR d'accès (route 6), en image. */
export function useQrAcces() {
  return useQuery({
    queryKey: ['/acces/qr', 'svg'],
    queryFn: async ({ signal }) => {
      const r = await fetch(adresseApi('/acces/qr'), { signal, credentials: 'same-origin' })
      return r.ok ? svgEnImage(await r.text()) : null
    },
  })
}
