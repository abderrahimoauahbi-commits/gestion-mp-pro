/** Essais de l'historique : l'auteur, chaque différence avant → après à la française, prix absents. */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { creerClientRequetes } from '../../lib/requetes'
import { Historique, type LigneHistorique } from './Historique'
import { libelleChamp, valeurLisible, type NomsHistorique } from './libellesHistorique'

function ligne(autres: Partial<LigneHistorique>): LigneHistorique {
  return {
    id: 1,
    quand: '2026-10-08T09:12:00',
    utilisateur: 'Karim BENALI',
    role: 'achats',
    action: 'modification matière',
    numero: '',
    detail: '',
    avant: null,
    apres: null,
    ...autres,
  }
}

function monter(reponse: LigneHistorique[], noms?: NomsHistorique) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => Response.json(reponse)),
  )
  render(
    <QueryClientProvider client={creerClientRequetes({ delaiRelance: 0 })}>
      <Historique objet="matiere" id={12} noms={noms} />
    </QueryClientProvider>,
  )
}

describe('Historique', () => {
  it('dit qui, quand, quoi, et chaque champ changé avant → après à la française', async () => {
    monter([
      ligne({
        detail: 'IMP 2900',
        avant: { prix: 2.5, date_livraison_prevue: '2026-10-20', stock_min: 5029.5, notes: null },
        apres: { prix: 2.8, date_livraison_prevue: '2026-10-25', stock_min: 6000, notes: 'Urgent' },
      }),
    ])
    expect(await screen.findByText('Modification matière')).toBeInTheDocument()
    expect(screen.getByText('08/10/2026 09:12 · Karim BENALI')).toBeInTheDocument()
    expect(screen.getByText('IMP 2900')).toBeInTheDocument()
    expect(screen.getByText(/^Prix :/)).toHaveTextContent('Prix : 2,50 → 2,80')
    expect(screen.getByText(/^Livraison prévue/)).toHaveTextContent(
      'Livraison prévue : 20/10/2026 → 25/10/2026',
    )
    expect(screen.getByText(/^Stock minimum/)).toHaveTextContent('5 029,5 → 6 000')
    expect(screen.getByText(/^Notes/)).toHaveTextContent('Notes : — → Urgent')
  })

  it('un prix retiré par le serveur (vide des deux côtés) n’apparaît pas', async () => {
    monter([
      ligne({
        utilisateur: 'Ahmed',
        avant: { prix: null, designation: 'Beige' },
        apres: { prix: null, designation: 'Beige clair' },
      }),
    ])
    expect(await screen.findByText(/^Désignation/)).toHaveTextContent('Désignation : Beige → Beige clair')
    expect(screen.queryByText(/Prix/)).not.toBeInTheDocument()
  })

  it('le plus récent en tête ; une création garde ses valeurs repliées, sans les vides', async () => {
    monter([
      ligne({ id: 1, action: 'création matière', apres: { id: 7, reference: 'IMP 2900', prix: null } }),
      ligne({ id: 2, quand: '2026-10-09T10:00:00', avant: { actif: true }, apres: { actif: false } }),
    ])
    const actions = await screen.findAllByRole('strong')
    expect(actions.map((a) => a.textContent)).toEqual(['Modification matière', 'Création matière'])
    expect(screen.getByText('En service', { exact: false })).toHaveTextContent('En service : oui → non')
    expect(screen.getByText('Valeurs à la création')).toBeInTheDocument()
    expect(screen.getByText('Référence : IMP 2900')).toBeInTheDocument()
    expect(screen.queryByText(/Prix/)).not.toBeInTheDocument()
  })

  it('un identifiant se lit par son nom quand la page le connaît', async () => {
    const noms = { fournisseur_id: new Map([[3, 'HASIRCI']]) }
    monter([ligne({ avant: { fournisseur_id: 3 }, apres: { fournisseur_id: 5 } })], noms)
    expect(await screen.findByText(/^Fournisseur/)).toHaveTextContent('Fournisseur : HASIRCI → 5')
  })

  it('sans ligne, le dit', async () => {
    monter([])
    expect(await screen.findByText('Aucune modification enregistrée.')).toBeInTheDocument()
  })

  it('valeurLisible : oui/non, vide, horodatage, prix, lignes ; libellés lisibles', () => {
    expect(valeurLisible(true)).toBe('oui')
    expect(valeurLisible('')).toBe('—')
    expect(valeurLisible('2026-10-08T14:05:00')).toBe('08/10/2026 14:05')
    expect(valeurLisible(0.0011, 'prix_kg')).toBe('0,0011')
    expect(valeurLisible(10.05, 'cours')).toBe('10,0500')
    expect(valeurLisible([{ role_id: 1 }, { role_id: 2 }], 'poids')).toBe('2 lignes')
    expect(libelleChamp('fournisseur_id')).toBe('Fournisseur')
    expect(libelleChamp('delai_mesure_jours')).toBe('Delai mesure jours')
  })
})
