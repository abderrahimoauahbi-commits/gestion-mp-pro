/** Essais de l'accès au serveur : en-tête, refus {detail, code}, réseau, session, heure. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  adresseApi,
  api,
  ENTETE_ANTI_FALSIFICATION,
  ErreurApi,
  messageErreur,
  PAS_DE_RESEAU,
  qs,
  SESSION_PERDUE,
} from './api'
import { aujourdhui, heureServeur } from './heure'

const repondre = (corps: unknown, statut = 200, entetes: Record<string, string> = {}) =>
  new Response(corps === undefined ? null : typeof corps === 'string' ? corps : JSON.stringify(corps), {
    status: statut,
    headers: { 'Content-Type': 'application/json', ...entetes },
  })

let appels: { url: string; init: RequestInit }[]
let reponses: (() => Response | Promise<Response>)[]

beforeEach(() => {
  appels = []
  reponses = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit) => {
      appels.push({ url, init })
      const suivante = reponses.shift()
      return suivante ? suivante() : repondre({})
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const entetes = (i = 0) => appels[i]!.init.headers as Record<string, string>

describe('En-tête anti-falsification et cookie', () => {
  it.each(['get', 'post', 'put', 'supprimer'] as const)(
    '%s porte X-Gestion-MP-PRO: 1 et le cookie',
    async (verbe) => {
      if (verbe === 'get') await api.get('/matieres')
      else if (verbe === 'put') await api.put('/matieres/1', { nom: 'x' })
      else await api[verbe]('/matieres/1')
      expect(ENTETE_ANTI_FALSIFICATION).toBe('X-Gestion-MP-PRO')
      expect(entetes()['X-Gestion-MP-PRO']).toBe('1')
      expect(appels[0]!.init.credentials).toBe('same-origin')
      expect(appels[0]!.url).toBe(verbe === 'get' ? '/api/matieres' : '/api/matieres/1')
    },
  )

  it('envoie le corps en JSON avec la méthode', async () => {
    await api.post('/commandes/12/envoyer', { version: 3 })
    expect(appels[0]!.init.method).toBe('POST')
    expect(appels[0]!.init.body).toBe('{"version":3}')
    expect(entetes()['Content-Type']).toBe('application/json')
  })

  it('envoie un fichier en multipart, sans poser le Content-Type', async () => {
    await api.envoyerFichier('/pieces/commande/12', new Blob(['%PDF']), 'bon.pdf')
    expect(appels[0]!.init.body).toBeInstanceOf(FormData)
    expect(entetes()['Content-Type']).toBeUndefined()
    expect(entetes()['X-Gestion-MP-PRO']).toBe('1')
  })

  it('pose les paramètres de lecture', async () => {
    await api.get('/stock', { date: '2026-10-08', q: '', magasin: null, alerte: true })
    expect(appels[0]!.url).toBe('/api/stock?date=2026-10-08&alerte=true')
  })
})

describe('Refus du serveur', () => {
  it('lit {detail, code} et garde le statut', async () => {
    reponses.push(() => repondre({ detail: 'Ce bon est clos.', code: 'bon_clos' }, 409))
    const e = await api.post('/commandes/1/envoyer').catch((x: unknown) => x)
    expect(e).toBeInstanceOf(ErreurApi)
    expect(e).toMatchObject({ message: 'Ce bon est clos.', code: 'bon_clos', statut: 409, passagere: false })
  })

  it('lit les champs fautifs d’une saisie refusée (422)', async () => {
    reponses.push(() =>
      repondre(
        {
          detail: 'quantite : doit être positive',
          code: 'saisie_invalide',
          champs: { 'lignes.0.quantite': 'doit être positive' },
        },
        422,
      ),
    )
    const e = await api.post('/ordres', {}).catch((x: unknown) => x)
    expect(e).toMatchObject({
      statut: 422,
      code: 'saisie_invalide',
      champs: { 'lignes.0.quantite': 'doit être positive' },
    })
  })

  it('joint les messages d’une validation brute', async () => {
    reponses.push(() => repondre({ detail: [{ msg: 'champ requis' }, { msg: 'trop long' }] }, 422))
    await expect(api.post('/x', {})).rejects.toThrow('champ requis · trop long')
  })

  it('sans corps lisible : « Erreur 502 »', async () => {
    reponses.push(() => new Response('<html>Bad Gateway</html>', { status: 502 }))
    const e = await api.get('/stock').catch((x: unknown) => x)
    expect(e).toMatchObject({ message: 'Erreur 502', statut: 502, code: null, passagere: true })
  })

  it('500 tracé : le message du serveur avec sa référence', async () => {
    reponses.push(() =>
      repondre({ detail: 'Erreur du serveur (réf. a1b2c3d4).', code: 'erreur_serveur' }, 500),
    )
    await expect(api.get('/stock')).rejects.toThrow('Erreur du serveur (réf. a1b2c3d4).')
  })

  it('réseau coupé : statut 0 et « Pas de réseau » dit comme tel', async () => {
    reponses.push(() => Promise.reject(new TypeError('Failed to fetch')))
    const e = await api.get('/stock').catch((x: unknown) => x)
    expect(e).toMatchObject({ statut: 0, code: 'pas_de_reseau', message: PAS_DE_RESEAU, passagere: true })
  })

  it('une lecture abandonnée reste abandonnée (pas « pas de réseau »)', async () => {
    reponses.push(() => Promise.reject(new DOMException('arrêt', 'AbortError')))
    await expect(api.get('/stock')).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('messageErreur dit toute erreur', () => {
    expect(messageErreur(new ErreurApi('Refusé.', 403))).toBe('Refusé.')
    expect(messageErreur('texte')).toBe('texte')
    expect(messageErreur(42)).toBe('Erreur inattendue.')
  })
})

describe('Session perdue', () => {
  it('un 401 prévient l’application, avec le motif du serveur', async () => {
    const recus: string[] = []
    const ecoute = (e: Event) => recus.push((e as CustomEvent<{ motif: string }>).detail.motif)
    window.addEventListener(SESSION_PERDUE, ecoute)
    reponses.push(() => repondre({ detail: 'Ce compte n’est plus actif.', code: 'compte_inactif' }, 401))
    await expect(api.get('/contexte')).rejects.toMatchObject({ statut: 401 })
    reponses.push(() => repondre({ detail: 'Identifiant ou code incorrect.', code: 'non_connecte' }, 401))
    await expect(api.post('/connexion', {})).rejects.toMatchObject({ statut: 401 })
    window.removeEventListener(SESSION_PERDUE, ecoute)
    expect(recus).toEqual(['Ce compte n’est plus actif.'])
  })
})

describe('Réponses', () => {
  it('204 : rien', async () => {
    reponses.push(() => new Response(null, { status: 204 }))
    await expect(api.post('/deconnexion')).resolves.toBeUndefined()
  })

  it('JSON : l’objet', async () => {
    reponses.push(() => repondre({ id: 3 }))
    await expect(api.get<{ id: number }>('/matieres/3')).resolves.toEqual({ id: 3 })
  })

  it('chaque réponse recale l’heure de l’usine (X-Heure-Serveur), refus compris', async () => {
    reponses.push(() =>
      repondre({ detail: 'Non.', code: 'droit_refuse' }, 403, {
        'X-Heure-Serveur': '2026-10-08T13:20:46+01:00',
      }),
    )
    await api.get('/x').catch(() => undefined)
    expect(aujourdhui()).toBe('2026-10-08')
    expect(heureServeur()).toMatch(/^13:20:4\d$/)
  })
})

describe('Adresses', () => {
  it('qs saute les vides et répète les listes', () => {
    expect(qs({})).toBe('')
    expect(qs({ q: 'frise rouge', vide: '', non: false, rien: null })).toBe('?q=frise+rouge')
    expect(qs({ lots: [1, 2] })).toBe('?lots=1&lots=2')
  })

  it('adresseApi pour les documents et exports', () => {
    expect(adresseApi('/documents/etiquettes', { lots: [1, 2] })).toBe(
      '/api/documents/etiquettes?lots=1&lots=2',
    )
  })
})
