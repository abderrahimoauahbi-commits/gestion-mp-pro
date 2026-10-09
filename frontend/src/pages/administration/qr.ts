/**
 * Un QR du serveur (SVG de segno) en image : le SVG servi n'a pas l'espace de noms
 * `xmlns`, sans lequel un navigateur ne l'affiche pas dans une balise `<img>` ; on l'ajoute.
 */
import { useQuery } from '@tanstack/react-query'

import { adresseApi } from '../../lib/api'

/** L'adresse `data:` d'un SVG, son espace de noms ajouté s'il manque. */
export function svgEnImage(svg: string): string {
  const complet = svg.includes('xmlns=')
    ? svg
    : svg.replace('<svg', '<svg xmlns="http://www.w3.org/2000/svg"')
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(complet)}`
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
