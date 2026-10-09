/** La page « à venir » d'un écran déclaré : titre, aide, onglets permis au rôle, lot qui la réalise. */
import { screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { fauxServeur, monterApp, prechargerPages, reponsesConnecte } from '../../essais/monter'
import { ongletsPermis } from '../../lib/droits'
import type { Role } from '../../lib/types'
import { ECRANS } from '../../routes'

beforeAll(prechargerPages)
afterEach(() => vi.unstubAllGlobals())

// Un écran du menu encore « à venir » (il porte le lot qui le réalisera), avec des onglets : les
// lots F remplacent ces pages une à une, l'essai prend celui qui reste.
const ROLES: readonly Role[] = ['alimentation', 'achats', 'direction']
const cas = ECRANS.flatMap((e) =>
  e.lot && e.groupe && e.onglets?.length && !e.atelier
    ? ROLES.filter((r) => e.roles.includes(r)).map((role) => ({ e, role }))
    : [],
)
  // Le cas le plus parlant d'abord : un rôle qui ne voit pas tous les onglets.
  .sort(
    (a, b) =>
      ongletsPermis(a.e, a.role).length -
      (a.e.onglets?.length ?? 0) -
      (ongletsPermis(b.e, b.role).length - (b.e.onglets?.length ?? 0)),
  )[0]

describe('EcranAVenir', () => {
  it.runIf(cas)('ne montre que les onglets permis au rôle', async () => {
    if (!cas) return
    const { e, role } = cas
    const permis = ongletsPermis(e, role)
    const dernier = permis[permis.length - 1]!
    fauxServeur(reponsesConnecte(role))
    monterApp(`${e.chemin}?onglet=${dernier.cle}`)
    expect(await screen.findByRole('heading', { level: 1, name: e.titre })).toBeInTheDocument()
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual(
      permis.map((o) => o.court ?? o.libelle),
    )
    expect(
      screen.getByText(`Cet écran arrive avec le lot ${e.lot} (onglet « ${dernier.libelle} »).`),
    ).toBeInTheDocument()
    expect(document.title).toBe(`${e.titre} — Gestion MP PRO`)
  })
})
