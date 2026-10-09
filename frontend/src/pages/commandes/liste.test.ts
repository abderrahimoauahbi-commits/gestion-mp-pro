/**
 * La liste et la fiche des bons sans écran : onglet d'un bon, indicateurs sur tous les bons,
 * onglet par défaut, messages après les gestes, corps de la modification (date absente / vidée),
 * prix et expédition (champ inchangé : absent).
 */
import { describe, expect, it } from 'vitest'

import { ficheEssai, resumeEssai } from './donneesEssai'
import { corpsLignes, ligneAjoutee, manquesLignes, versFormeLignes } from './formeLignes'
import { enRetard, indicateurs, ongletDe, premierOnglet } from './liste'
import { apresEnvoi, apresModification, apresPrix, apresSuivi } from './messages'
import { corpsExpedition, versFormeExpedition } from './VoletExpedition'
import { corpsPrix, questionPrix, reprendreCatalogue, versFormePrix } from './VoletPrix'

describe('Liste des bons', () => {
  it('onglet d’un bon ; soldé et annulé ensemble ; le premier onglet non vide par défaut', () => {
    expect(ongletDe({ statut: 'soldee' })).toBe('clos')
    expect(ongletDe({ statut: 'annulee' })).toBe('clos')
    expect(ongletDe({ statut: 'a_approuver' })).toBe('a_approuver')
    expect(premierOnglet([resumeEssai({ statut: 'confirmee' })])).toBe('confirmee')
    expect(premierOnglet([])).toBe('brouillon')
  })

  it('indicateurs sur tous les bons : ouverts, engagé (partis), prix à confirmer, retard', () => {
    const i = indicateurs([
      resumeEssai({ statut: 'brouillon', parti: false, montant_estime_mad: 1000, reste_estime_mad: 1000 }),
      resumeEssai({ statut: 'a_approuver', parti: false }),
      resumeEssai({
        statut: 'envoyee',
        parti: true,
        montant_estime_mad: 500,
        reste_estime_mad: 400,
        prix_a_confirmer: 1,
        livraison: 'en_retard',
      }),
      resumeEssai({ statut: 'soldee', parti: true, montant_estime_mad: 9999, reste_estime_mad: 0 }),
    ])
    expect(i).toMatchObject({
      ouverts: 3,
      brouillons: 1,
      aApprouver: 1,
      engage: 500,
      partis: 1,
      reste: 400,
      aConfirmer: 1,
      retard: 1,
    })
    expect(enRetard({ livraison: 'partiel_retard' })).toBe(true)
  })
})

describe('Messages après un geste', () => {
  const avant = ficheEssai({ statut: 'a_approuver', numero: null })
  it('modification : renvoyé en brouillon, ramené, au-delà du seuil, déjà parti', () => {
    expect(apresModification(avant, ficheEssai({ statut: 'brouillon', numero: null }))).toMatch(
      /revient en brouillon/,
    )
    expect(
      apresModification(ficheEssai({ statut: 'a_approuver' }), ficheEssai({ statut: 'envoyee' })),
    ).toMatch(/ramené/)
    expect(
      apresModification(
        ficheEssai({ statut: 'brouillon', numero: null }),
        ficheEssai({ statut: 'a_approuver', numero: null }),
      ),
    ).toMatch(/repasse par la direction/)
    expect(apresModification(ficheEssai(), ficheEssai())).toMatch(/réimprimez-le/)
  })
  it('envoi, prix, suivi', () => {
    expect(apresEnvoi(ficheEssai({ statut: 'a_approuver', numero: null }))).toBe(
      'Bon soumis à la direction : il partira à son approbation.',
    )
    expect(apresEnvoi(ficheEssai({ numero: 'BC-2026-0009', date_commande: '2026-10-08' }))).toMatch(
      /n° BC-2026-0009, daté du 08\/10\/2026/,
    )
    expect(apresPrix(2, 1, 0)).toBe('2 prix confirmé(s), 1 reporté(s) au catalogue.')
    expect(apresSuivi(null, '2026-11-20')).toMatch(/ETA\) du 20\/11\/2026/)
    expect(apresSuivi('2026-11-20', '2026-11-20')).toBe('Suivi de l’expédition enregistré.')
  })
})

describe('Saisies de la fiche', () => {
  it('lignes : la date absente si inchangée, `null` si vidée ; une quantité à chaque ligne', () => {
    const c = ficheEssai({ modifiable: true })
    const f = versFormeLignes(c)
    expect(corpsLignes(f, f, 5)).not.toHaveProperty('date_livraison_prevue')
    expect(corpsLignes({ ...f, livraison: '' }, f, 5)).toMatchObject({
      version: 5,
      date_livraison_prevue: null,
    })
    expect(corpsLignes(f, f, 5).lignes[1]).toEqual({
      matiere_id: 6,
      quantite: 1000,
      unite_achat: 'Bobine',
      contenance: 5,
    })
    expect(manquesLignes({ ...f, lignes: [{ ...f.lignes[0]!, quantite: 0 }] })).toHaveLength(1)
    expect(
      ligneAjoutee({
        id: 3,
        poids_bobine: 0,
        bobines_palette: 0,
        unite_achat: 'kg',
        contenance_achat: 0,
        minimum_commande: 50,
      } as never),
    ).toMatchObject({ unite: 'kg', quantite: 50 })
  })

  it('prix : au kilo, report au catalogue, question ; reprendre le catalogue dans la devise du bon', () => {
    const c = ficheEssai()
    const f = versFormePrix(c)
    expect(Object.values(f.prix)).toEqual([27.5, 12])
    const vide = { ...f, prix: { '5': null, '6': 13 } }
    expect(corpsPrix(c, vide, 5)).toEqual({
      version: 5,
      lignes: [{ ligne_id: 6, prix: 13, unite: 'kg' }],
      mettre_a_jour_catalogue: true,
    })
    expect(questionPrix(c, vide)).toBe(
      'Confirmer 1 prix ? Le prix du catalogue changera pour : JUTE TRAME Naturel.',
    )
    expect(reprendreCatalogue(c, vide).prix['5']).toBe(27.5)
  })

  it('expédition : seuls les jalons changés partent, un champ vidé vaut `null`', () => {
    const c = ficheEssai({
      expedition: { ...ficheEssai().expedition, eta: '2026-11-01', conteneur: 'MSCU1' },
    })
    const f = versFormeExpedition(c)
    expect(corpsExpedition({ ...f, eta: '', navire: 'MSC Anna' }, f, 3)).toEqual({
      version: 3,
      eta: null,
      navire: 'MSC Anna',
    })
  })
})
