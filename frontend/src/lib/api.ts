/**
 * Accès au serveur : une seule façon d'appeler, une seule façon d'échouer.
 *
 * - La session tient dans un cookie `HttpOnly` que le navigateur porte seul (`same-origin`).
 * - Chaque requête part avec l'en-tête anti-falsification `X-Gestion-MP-PRO: 1` : une page d'un
 *   autre site ne peut pas l'ajouter, elle ne peut donc pas faire agir quelqu'un de connecté à son
 *   insu (le serveur refuse toute écriture sans lui, ARCHITECTURE § 5.4).
 * - Chaque réponse recale l'heure de l'usine (`X-Heure-Serveur`, `lib/heure.ts`).
 * - Un refus du serveur arrive en `{detail, code}` (+ `champs` pour une saisie, API-PRO § 0.3) et
 *   devient une `ErreurApi` dont le message est affiché tel quel ; le réseau coupé a le statut 0.
 * - Un 401 hors connexion prévient l'application (`SESSION_PERDUE`) avec le motif du serveur.
 */
import { recalerHorloge } from './heure'

/** L'en-tête que le serveur exige sur toute écriture. */
export const ENTETE_ANTI_FALSIFICATION = 'X-Gestion-MP-PRO'

/** L'événement envoyé sur `window` quand il faut se reconnecter ; `detail.motif` dit pourquoi. */
export const SESSION_PERDUE = 'gestion-mp-pro:session-perdue'

/** Le message d'un serveur injoignable (statut 0), distinct d'une liste vide. */
export const PAS_DE_RESEAU = 'Le serveur ne répond pas : vérifiez le réseau (Wi-Fi ou 4G/5G).'

/** Les chemins où un 401 est une réponse attendue (mauvais code), pas une session perdue. */
const SANS_SESSION = ['/connexion', '/installation', '/appareils/enroler']

type Parametre = string | number | boolean | null | undefined

/** Un refus du serveur, ou l'absence de réseau (`statut` 0). */
export class ErreurApi extends Error {
  /** Statut HTTP ; 0 quand le serveur n'a pas répondu. */
  readonly statut: number
  /** Code stable du refus (`conflit_version`, `stock_insuffisant`…), si le serveur l'a donné. */
  readonly code: string | null
  /** Pour une saisie refusée (422) : chemin du champ → message, pour surligner le champ. */
  readonly champs: Record<string, string>

  constructor(
    message: string,
    statut: number,
    code: string | null = null,
    champs: Record<string, string> = {},
  ) {
    super(message)
    this.name = 'ErreurApi'
    this.statut = statut
    this.code = code
    this.champs = champs
  }

  /** Pas de réseau, ou serveur en panne : on peut réessayer. */
  get passagere(): boolean {
    return this.statut === 0 || this.statut >= 500
  }
}

/** Le message à dire pour toute erreur, d'où qu'elle vienne. */
export function messageErreur(e: unknown): string {
  if (e instanceof Error) return e.message
  return typeof e === 'string' ? e : 'Erreur inattendue.'
}

/** Une chaîne de requête qui saute les valeurs vides (`''`, `null`, `undefined`, `false`). */
export function qs(params: Record<string, Parametre | Parametre[]> = {}): string {
  const p = new URLSearchParams()
  for (const [cle, valeur] of Object.entries(params)) {
    for (const v of Array.isArray(valeur) ? valeur : [valeur]) {
      if (v === '' || v == null || v === false) continue
      p.append(cle, String(v))
    }
  }
  const texte = p.toString()
  return texte ? `?${texte}` : ''
}

/** L'adresse complète d'une route (documents à imprimer, exports Excel). */
export function adresseApi(chemin: string, params?: Record<string, Parametre | Parametre[]>): string {
  return `/api${chemin}${qs(params)}`
}

const estObjet = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

/** Le texte d'un message de validation FastAPI brut (`[{loc, msg}]`), au cas où il passerait. */
function messagesDeValidation(liste: unknown[]): string {
  return liste
    .map((d) => (estObjet(d) && typeof d.msg === 'string' ? d.msg : ''))
    .filter(Boolean)
    .join(' · ')
}

/** Lit le corps d'un refus : `{detail, code, champs}` ; sinon « Erreur 502 ». */
async function lireRefus(reponse: Response): Promise<ErreurApi> {
  let message = `Erreur ${reponse.status}`
  let code: string | null = null
  const champs: Record<string, string> = {}
  try {
    const corps: unknown = await reponse.json()
    if (estObjet(corps)) {
      if (typeof corps.detail === 'string') message = corps.detail
      else if (Array.isArray(corps.detail)) message = messagesDeValidation(corps.detail) || message
      if (typeof corps.code === 'string') code = corps.code
      if (estObjet(corps.champs)) {
        for (const [cle, texte] of Object.entries(corps.champs))
          if (typeof texte === 'string') champs[cle] = texte
      }
    }
  } catch {
    /* réponse sans corps JSON (relais, page d'erreur) : on garde le statut */
  }
  return new ErreurApi(message, reponse.status, code, champs)
}

interface Options {
  methode?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  corps?: unknown
  signal?: AbortSignal
}

/** L'appel unique : en-tête, cookie, heure du serveur, refus lisibles. */
export async function requete<T>(
  chemin: string,
  { methode = 'GET', corps, signal }: Options = {},
): Promise<T> {
  const entetes: Record<string, string> = { [ENTETE_ANTI_FALSIFICATION]: '1', Accept: 'application/json' }
  let body: BodyInit | undefined
  if (corps instanceof FormData) body = corps
  else if (corps !== undefined) {
    entetes['Content-Type'] = 'application/json'
    body = JSON.stringify(corps)
  }
  let reponse: Response
  try {
    reponse = await fetch(`/api${chemin}`, {
      method: methode,
      credentials: 'same-origin',
      headers: entetes,
      body,
      signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ErreurApi(PAS_DE_RESEAU, 0, 'pas_de_reseau')
  }
  recalerHorloge(reponse.headers.get('X-Heure-Serveur'))
  if (!reponse.ok) {
    const refus = await lireRefus(reponse)
    if (reponse.status === 401 && !SANS_SESSION.some((c) => chemin.startsWith(c))) {
      window.dispatchEvent(new CustomEvent(SESSION_PERDUE, { detail: { motif: refus.message } }))
    }
    throw refus
  }
  if (reponse.status === 204 || reponse.headers.get('Content-Length') === '0') {
    // Une réponse sans corps : l'appelant qui l'attend déclare `void` ou `undefined`.
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
    return undefined as T
  }
  return reponse.json()
}

/** Les quatre verbes de l'API (PATCH n'est pas employé, API-PRO § 0.1) et l'envoi de fichier. */
export const api = {
  get: <T>(chemin: string, params?: Record<string, Parametre | Parametre[]>, signal?: AbortSignal) =>
    requete<T>(`${chemin}${qs(params)}`, { signal }),
  post: <T>(chemin: string, corps?: unknown) => requete<T>(chemin, { methode: 'POST', corps }),
  put: <T>(chemin: string, corps: unknown) => requete<T>(chemin, { methode: 'PUT', corps }),
  supprimer: <T = void>(chemin: string, corps?: unknown) => requete<T>(chemin, { methode: 'DELETE', corps }),
  /** Une pièce jointe (multipart, champ `fichier`) ; le navigateur pose lui-même le Content-Type. */
  envoyerFichier: <T>(chemin: string, fichier: Blob, nom?: string, champ = 'fichier') => {
    const formulaire = new FormData()
    if (nom) formulaire.append(champ, fichier, nom)
    else formulaire.append(champ, fichier)
    return requete<T>(chemin, { methode: 'POST', corps: formulaire })
  },
}
