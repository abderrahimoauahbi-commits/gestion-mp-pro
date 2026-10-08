/** Essais de Champ (et des contrôles simples) : libellé = nom accessible, aide et erreur en description. */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { ErreurApi } from '../../lib/api'
import { Champ, erreurDuChamp } from './Champ'
import { Saisie } from './Saisie'
import { Zone } from './Zone'

describe('Champ', () => {
  it('le libellé nomme le contrôle ; l’aide le décrit ; « * » si obligatoire', () => {
    render(
      <Champ libelle="Référence" aide="Composée à partir de la classification." obligatoire>
        <Saisie valeur="" onChange={() => {}} />
      </Champ>,
    )
    const champ = screen.getByRole('textbox', { name: /Référence/ })
    expect(champ).toHaveAccessibleDescription('Composée à partir de la classification.')
    expect(champ).toHaveAttribute('aria-required', 'true')
    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('l’erreur du serveur s’écrit sous le champ et le marque invalide', () => {
    const refus = new ErreurApi('Saisie refusée.', 422, 'saisie_invalide', {
      'lignes.0.kg': 'Au moins 0,1 kg.',
    })
    render(
      <Champ libelle="Quantité" erreur={erreurDuChamp(refus, 'lignes.0.kg')}>
        <Saisie valeur="0" onChange={() => {}} />
      </Champ>,
    )
    const champ = screen.getByRole('textbox', { name: 'Quantité' })
    expect(champ).toHaveAttribute('aria-invalid', 'true')
    expect(champ).toHaveAccessibleDescription('Au moins 0,1 kg.')
    expect(erreurDuChamp(new Error('x'), 'a')).toBeUndefined()
  })

  it('Saisie et Zone rendent ce qu’on tape ; Zone compte les caractères', async () => {
    function Essai() {
      const [nom, setNom] = useState('')
      const [obs, setObs] = useState('')
      return (
        <>
          <Champ libelle="Nom">
            <Saisie valeur={nom} onChange={setNom} />
          </Champ>
          <Champ libelle="Observations">
            <Zone valeur={obs} onChange={setObs} max={200} />
          </Champ>
        </>
      )
    }
    render(<Essai />)
    await userEvent.type(screen.getByRole('textbox', { name: 'Nom' }), 'MAZARI')
    expect(screen.getByRole('textbox', { name: 'Nom' })).toHaveValue('MAZARI')
    await userEvent.type(screen.getByRole('textbox', { name: 'Observations' }), 'Bobines humides')
    expect(screen.getByText('15 / 200 caractères')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Observations' })).toHaveAccessibleDescription(
      '15 / 200 caractères',
    )
  })
})
