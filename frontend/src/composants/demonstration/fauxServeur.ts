/** Un faux serveur pour la démonstration : quelques réponses de l'API, le reste en « Pas de réseau ». */
import { ajouterJours, aujourdhui } from '../../lib/heure'

const PIECES = [
  {
    id: 1,
    nom: 'facture-HASIRCI-0912.pdf',
    genre: 'PDF',
    taille: 254_000,
    par: 'Karim',
    joint_le: '2026-10-07T14:05:00',
  },
  {
    id: 2,
    nom: 'photo-bobines-mouillées.jpg',
    genre: 'Image',
    taille: 3_400_000,
    par: 'Mohamed',
    joint_le: '2026-10-08T09:12:00',
  },
]

const HISTORIQUE = [
  {
    id: 2,
    quand: '2026-10-08T09:12:00',
    par: 'Karim',
    action: 'Bon modifié',
    changements: [
      { libelle: 'Livraison prévue', avant: '2026-10-20', apres: '2026-10-25' },
      { libelle: 'Quantité (kg)', avant: 5029.5, apres: 6000 },
    ],
  },
  {
    id: 1,
    quand: '2026-10-07T16:40:00',
    par: 'Mohamed',
    action: 'Bon envoyé',
    detail: 'BC-2026-0012 envoyé à HASIRCI.',
  },
]

const LOTS = Array.from({ length: 8 }, (_, i) => ({
  id: 100 + i,
  numero: `LOT-2026-${String(40 + i).padStart(4, '0')}`,
  reste_kg: 120.5 + i * 37.25,
  date_entree: ajouterJours(aujourdhui(), -60 + i * 7),
  magasin: 'Principal',
  quarantaine: i === 3,
}))

function repondre(chemin: string): unknown {
  if (chemin.startsWith('/api/pieces')) return PIECES
  if (chemin.startsWith('/api/historique/')) return HISTORIQUE
  if (chemin.startsWith('/api/lots/disponibles')) return LOTS
  return undefined
}

/** Remplace `fetch` pour les adresses connues ; un envoi (POST, DELETE) réussit sans rien changer. */
export function installerFauxServeur(): void {
  const vrai = window.fetch.bind(window)
  window.fetch = async (entree, init) => {
    const chemin = typeof entree === 'string' ? entree : entree instanceof URL ? entree.pathname : entree.url
    const methode = init?.method ?? 'GET'
    if (methode !== 'GET' && chemin.startsWith('/api/')) return new Response(null, { status: 204 })
    const corps = repondre(chemin)
    if (corps === undefined) return vrai(entree, init)
    await new Promise((ok) => setTimeout(ok, 250))
    return Response.json(corps)
  }
}
