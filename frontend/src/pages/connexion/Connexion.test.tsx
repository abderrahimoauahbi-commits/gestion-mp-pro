/**
 * La connexion (H-01, P1-6, P1-26) : visages ou identifiant, l'alimentation entre au 4e chiffre
 * exactement, les autres par Entrée ; refus dit sous le champ, code vidé ; installation.
 */
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { fauxServeur, moiDe, monterApp, prechargerPages } from '../../essais/monter'
import { libelleCode } from './commun'
import { corpsDuVisage, entreeAuQuatrieme } from './Formulaires'
import { identifiantDe, manqueInstallation } from './Installation'

beforeAll(prechargerPages)
afterEach(() => vi.unstubAllGlobals())

const NON_CONNECTE = {
  statut: 401,
  corps: { detail: 'Connectez-vous pour continuer.', code: 'non_connecte' },
}
const VISAGES = [
  { id: 1, nom: 'MAZARI', role: 'direction', role_libelle: 'Direction', longueur_code: null },
  { id: 3, nom: 'Ahmed', role: 'alimentation', role_libelle: 'Alimentation des machines', longueur_code: 4 },
  { id: 2, nom: 'Karim BENALI', role: 'achats', role_libelle: 'Achats', longueur_code: null },
]

function serveur(autres = {}) {
  return fauxServeur({
    'GET /etat': { corps: { installe: true, societe: 'Tapis de l’Atlas' } },
    'GET /visages': { corps: VISAGES },
    'GET /contexte': NON_CONNECTE,
    ...autres,
  })
}

describe('Connexion', () => {
  it('règles : élision, entrée au 4e chiffre, corps de la connexion', () => {
    expect(libelleCode('Ahmed')).toBe('Code d’Ahmed')
    expect(libelleCode('Karim')).toBe('Code de Karim')
    expect(libelleCode('Hicham')).toBe('Code d’Hicham')
    const ahmed = {
      id: 3,
      nom: 'A',
      role: 'alimentation',
      role_libelle: 'Alimentation des machines',
    } as const
    expect(entreeAuQuatrieme({ ...ahmed, longueur_code: 4 })).toBe(true)
    expect(entreeAuQuatrieme({ ...ahmed, longueur_code: 5 })).toBe(false)
    expect(
      entreeAuQuatrieme({ id: 2, nom: 'K', role: 'achats', role_libelle: 'Achats', longueur_code: null }),
    ).toBe(false)
    expect(corpsDuVisage({ ...ahmed, longueur_code: 4 }, '1234')).toEqual({
      compte: 3,
      identifiant: '',
      code: '1234',
    })
  })

  it('l’alimentation entre au 4e chiffre, sans Entrée', async () => {
    const appels = serveur({ 'POST /connexion': { corps: moiDe('alimentation') } })
    const app = monterApp('/connexion')
    await userEvent.click(await screen.findByRole('button', { name: /Ahmed/ }))
    const code = screen.getByLabelText('Code d’Ahmed')
    expect(code).toHaveAttribute('inputmode', 'numeric')
    await userEvent.type(code, '123')
    expect(appels.some((a) => a.chemin === '/connexion')).toBe(false)
    await userEvent.type(code, '4')
    await waitFor(() => expect(app.adresse()).toBe('/accueil'))
    expect(appels.find((a) => a.chemin === '/connexion')?.corps).toEqual({
      compte: 3,
      identifiant: '',
      code: '1234',
    })
  })

  it('les achats entrent par Entrée ; un refus est dit et le code vidé', async () => {
    const appels = serveur({
      'POST /connexion': {
        statut: 401,
        corps: { detail: 'Identifiant ou code incorrect.', code: 'non_connecte' },
      },
    })
    monterApp('/connexion')
    await userEvent.click(await screen.findByRole('button', { name: /Karim BENALI/ }))
    const code = screen.getByLabelText('Code de Karim BENALI')
    expect(screen.getByRole('button', { name: 'Entrer' })).toHaveAttribute(
      'data-raison',
      'À renseigner : votre code.',
    )
    await userEvent.type(code, '1234')
    expect(appels.some((a) => a.chemin === '/connexion')).toBe(false)
    await userEvent.type(code, '{Enter}')
    expect(await screen.findByText('Identifiant ou code incorrect.')).toBeInTheDocument()
    expect(code).toHaveValue('')
  })

  it('hors du poste local : identifiant et code', async () => {
    const appels = serveur({
      'GET /visages': { corps: [] },
      'POST /connexion': { corps: moiDe('direction') },
    })
    const app = monterApp('/connexion')
    await userEvent.type(await screen.findByLabelText('Identifiant'), ' Mazari ')
    expect(screen.getByText(/tapez votre identifiant et votre code/)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Code'), 'codedirection{Enter}')
    await waitFor(() => expect(app.adresse()).toBe('/cockpit'))
    expect(appels.find((a) => a.chemin === '/connexion')?.corps).toEqual({
      identifiant: 'mazari',
      code: 'codedirection',
    })
  })

  it('le serveur muet se dit comme tel', async () => {
    fauxServeur({ 'GET /etat': { statut: 502, corps: { detail: 'arrêté', code: 'serveur_absent' } } })
    monterApp('/connexion')
    expect(
      await screen.findByText('Le serveur ne répond pas. Vérifiez le réseau, puis rechargez la page.'),
    ).toBeInTheDocument()
  })
})

describe('Installation', () => {
  it('l’identifiant retenu et ce qui manque', () => {
    expect(identifiantDe('Mohamed  Él Mazari')).toBe('mohamed.el.mazari')
    expect(manqueInstallation('M', 'court')).toEqual([
      'votre nom (2 caractères au moins)',
      'un code de 8 caractères au moins',
    ])
    expect(manqueInstallation('MAZARI', 'codedirection')).toEqual([])
  })

  it('sans compte, la connexion mène à l’installation, qui crée la direction et entre au Cockpit', async () => {
    let installe = false
    const appels = fauxServeur({
      'GET /etat': () => ({ corps: { installe, societe: '' } }),
      'GET /contexte': NON_CONNECTE,
      'POST /installation': () => {
        installe = true
        return { corps: moiDe('direction') }
      },
    })
    const app = monterApp('/connexion')
    await waitFor(() => expect(app.adresse()).toBe('/installation'))
    await userEvent.type(await screen.findByLabelText(/Votre nom/), 'MAZARI')
    expect(screen.getByText('Ce qui vous désigne à la connexion. Retenu : « mazari ».')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/^Code/), 'codedirection')
    await userEvent.click(screen.getByRole('button', { name: 'Créer le compte et entrer' }))
    await waitFor(() => expect(app.adresse()).toBe('/cockpit'))
    expect(appels.find((a) => a.chemin === '/installation')?.corps).toEqual({
      societe: '',
      nom: 'MAZARI',
      identifiant: 'mazari',
      code: 'codedirection',
    })
  })
})
