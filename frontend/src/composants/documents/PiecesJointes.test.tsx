/** Essais des pièces jointes : liste, refus avant envoi (taille, SVG), envoi multipart, bilan, retrait confirmé. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { Messages } from '../retour/Messages'
import { PiecesJointes, refusAvantEnvoi, tailleLisible, TAILLE_MAX } from './PiecesJointes'

const PIECES = [
  { id: 5, nom: 'facture.pdf', genre: 'PDF', taille: 254_000, par: 'Karim', joint_le: '2026-10-07T14:05:00' },
]

function serveur() {
  const appels: { adresse: string; methode: string; corps?: BodyInit | null }[] = []
  const fetch = vi.fn(async (adresse: string, init?: RequestInit) => {
    appels.push({ adresse, methode: init?.method ?? 'GET', corps: init?.body })
    if (init?.method === 'DELETE') return new Response(null, { status: 204 })
    if (init?.method === 'POST') return Response.json({ id: 6 })
    return Response.json(PIECES)
  })
  vi.stubGlobal('fetch', fetch)
  return appels
}

function monter(lectureSeule = false) {
  render(
    <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
      <MemoryRouter>
        <Messages />
        <PiecesJointes objet="commande" id={12} lectureSeule={lectureSeule} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PiecesJointes', () => {
  it('liste les documents : lien de téléchargement, taille lisible, date à la française', async () => {
    const appels = serveur()
    monter()
    const lien = await screen.findByRole('link', { name: 'facture.pdf' })
    expect(lien).toHaveAttribute('href', '/api/pieces/5/fichier')
    expect(screen.getByText('248 Ko')).toBeInTheDocument()
    expect(screen.getByText('07/10/2026 14:05')).toBeInTheDocument()
    expect(appels[0]?.adresse).toBe('/api/pieces?objet=commande&id=12')
  })

  it('refuse avant l’envoi un SVG et un fichier trop lourd ; envoie le reste en multipart ; dit le bilan', async () => {
    const appels = serveur()
    monter()
    await screen.findByRole('link', { name: 'facture.pdf' })
    const utilisateur = userEvent.setup({ applyAccept: false })
    const lourd = new File(['x'], 'plan.pdf', { type: 'application/pdf' })
    Object.defineProperty(lourd, 'size', { value: TAILLE_MAX + 1 })
    await utilisateur.upload(screen.getByLabelText('Joindre un document…'), [
      new File(['<svg/>'], 'logo.svg', { type: 'image/svg+xml' }),
      lourd,
      new File(['%PDF'], 'bl.pdf', { type: 'application/pdf' }),
    ])
    const envoi = appels.find((a) => a.methode === 'POST')
    expect(envoi?.adresse).toBe('/api/pieces')
    expect(envoi?.corps).toBeInstanceOf(FormData)
    const corps = envoi?.corps instanceof FormData ? envoi.corps : null
    expect(corps?.get('objet')).toBe('commande')
    expect(corps?.get('id')).toBe('12')
    expect(appels.filter((a) => a.methode === 'POST')).toHaveLength(1)
    expect(
      await screen.findByText(/^1 joint, 2 refusés : « logo\.svg » : type de fichier refusé/),
    ).toBeInTheDocument()
  })

  it('retirer se confirme sur place, puis la liste se relit', async () => {
    const appels = serveur()
    monter()
    await screen.findByRole('link', { name: 'facture.pdf' })
    await userEvent.click(screen.getByRole('button', { name: 'Retirer' }))
    await userEvent.click(screen.getByRole('button', { name: 'Oui, retirer' }))
    expect(await screen.findByText('« facture.pdf » retiré.')).toBeInTheDocument()
    expect(appels.some((a) => a.methode === 'DELETE' && a.adresse === '/api/pieces/5')).toBe(true)
  })

  it('en lecture seule, ni joindre ni retirer', async () => {
    serveur()
    monter(true)
    await screen.findByRole('link', { name: 'facture.pdf' })
    expect(screen.queryByText('Joindre un document…')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Retirer' })).toBeNull()
  })

  it('tailles et refus avant envoi', () => {
    expect(tailleLisible(512)).toBe('512\u00a0o')
    expect(tailleLisible(3.2 * 1024 * 1024)).toBe('3,2\u00a0Mo')
    expect(refusAvantEnvoi({ name: 'Photo.HEIC', size: 10 })).toBe('')
    expect(refusAvantEnvoi({ name: 'script.exe', size: 10 })).toMatch(/type de fichier refusé/)
  })
})
