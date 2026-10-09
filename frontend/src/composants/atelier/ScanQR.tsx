/**
 * Lire le QR d'une étiquette de lot avec la caméra du téléphone (`/atelier/chercher`). L'étiquette
 * porte l'adresse `/lot/{id}` ; `lotDuQR` en tire l'identifiant. Un QR qui porte autre chose (le
 * numéro d'un lot, l'étiquette d'un fournisseur) est relu par le serveur (`GET /lots/scan`, route
 * 110, an. 19) : un lot → sa fiche ; aucun → « Aucun lot pour cette étiquette ({texte lu}). » ;
 * plusieurs → « {n} lots portent ce numéro : choisir ci-dessous », `onPlusieurs(numéro)` filtre la
 * liste de la page, et le scan continue. La caméra passe par
 * `BarcodeDetector` (Chrome Android, Safari récent) ; sans lui, ou sans caméra permise, l'écran
 * le dit et la recherche par numéro reste la voie normale.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

import { api, ErreurApi, messageErreur } from '../../lib/api'
import type { Schema } from '../../lib/types'
import { Bouton } from '../saisie/Bouton'
import styles from './ScanQR.module.css'

/** L'identifiant du lot d'un QR (`…/lot/123`, `/atelier/lots/123`), ou `null`. */
export function lotDuQR(texte: string): number | null {
  const m = texte.trim().match(/\/lots?\/(\d+)(?:[/?#]|$)/)
  return m?.[1] ? Number(m[1]) : null
}

/** Ce qu'une étiquette lue désigne : un lot, ou une phrase à dire (et le numéro à chercher). */
export type Lecture = { lot: number } | { message: string; plusieurs?: string }

/** Relit un texte de QR : l'adresse d'une étiquette, sinon le serveur (route 110). */
export async function lireEtiquette(texte: string): Promise<Lecture> {
  const id = lotDuQR(texte)
  if (id != null) return { lot: id }
  const code = texte.trim()
  try {
    const lots = await api.get<Schema<'LotResume'>[]>('/lots/scan', { code })
    const [seul] = lots
    if (lots.length === 1 && seul) return { lot: seul.lot_id }
    if (lots.length > 1)
      return { message: `${lots.length} lots portent ce numéro : choisir ci-dessous`, plusieurs: code }
  } catch (e) {
    if (!(e instanceof ErreurApi) || e.statut !== 404) throw e
  }
  return { message: `Aucun lot pour cette étiquette (${code}).` }
}

interface Detecteur {
  detect: (source: HTMLVideoElement) => Promise<{ rawValue: string }[]>
}
type ConstructeurDetecteur = new (options: { formats: string[] }) => Detecteur

const estConstructeur = (x: unknown): x is ConstructeurDetecteur => typeof x === 'function'

/** Le détecteur de QR du navigateur, s'il en a un. */
export function detecteurDisponible(): ConstructeurDetecteur | null {
  const d: unknown = Reflect.get(window, 'BarcodeDetector')
  return estConstructeur(d) && typeof navigator.mediaDevices?.getUserMedia === 'function' ? d : null
}

/** La caméra arrière filmée dans `video`, lue toutes les 300 ms jusqu'à un QR de lot. */
function useCamera(active: boolean, onTexte: (texte: string) => void, onEchec: (m: string) => void) {
  const video = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const Classe = detecteurDisponible()
    if (!active || !Classe) return
    let flux: MediaStream | null = null
    let minuterie: ReturnType<typeof setInterval> | undefined
    const detecteur = new Classe({ formats: ['qr_code'] })
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((f) => {
        flux = f
        if (!video.current) return
        video.current.srcObject = f
        void video.current.play()
        minuterie = setInterval(() => {
          if (!video.current) return
          void detecteur.detect(video.current).then((codes) => {
            const lu = codes.map((c) => c.rawValue.trim()).find(Boolean)
            if (lu) onTexte(lu)
          })
        }, 300)
      })
      .catch(() =>
        onEchec(
          'La caméra n’est pas permise : autorisez-la dans les réglages du téléphone, ou tapez le numéro du lot.',
        ),
      )
    return () => {
      clearInterval(minuterie)
      flux?.getTracks().forEach((t) => t.stop())
    }
  }, [active, onTexte, onEchec])
  return video
}

/** Un texte lu n'est relu qu'une fois tant qu'il reste devant la caméra. */
function useLectures(onLot: (id: number) => void, onPlusieurs?: (numero: string) => void) {
  const [message, setMessage] = useState('')
  const dernier = useRef('')
  const rappels = useRef({ onLot, onPlusieurs })
  useEffect(() => {
    rappels.current = { onLot, onPlusieurs }
  })
  const onTexte = useCallback((texte: string) => {
    if (texte === dernier.current) return
    dernier.current = texte
    lireEtiquette(texte)
      .then((r) => {
        if ('lot' in r) {
          rappels.current.onLot(r.lot)
          return
        }
        setMessage(r.message)
        if (r.plusieurs) rappels.current.onPlusieurs?.(r.plusieurs)
      })
      .catch((e: unknown) => {
        dernier.current = ''
        setMessage(messageErreur(e))
      })
  }, [])
  return { message, onTexte }
}

export function ScanQR({
  onLot,
  onPlusieurs,
}: {
  onLot: (id: number) => void
  /** Plusieurs lots portent le numéro lu : la page filtre sa liste sur lui. */
  onPlusieurs?: (numero: string) => void
}) {
  const [active, setActive] = useState(false)
  const [echec, setEchec] = useState('')
  const { message, onTexte } = useLectures(onLot, onPlusieurs)
  const video = useCamera(active, onTexte, setEchec)
  if (!detecteurDisponible()) {
    return (
      <p className={styles.note}>Ce téléphone ne lit pas les QR depuis l’écran : tapez le numéro du lot.</p>
    )
  }
  return (
    <div className={styles.scan}>
      {active && !echec ? (
        <video
          ref={video}
          className={styles.video}
          muted
          playsInline
          aria-label="Caméra : visez le QR de l’étiquette"
        />
      ) : null}
      {echec ? <p className={styles.note}>{echec}</p> : null}
      {message && !echec ? (
        <p className={styles.note} role="status">
          {message}
        </p>
      ) : null}
      <Bouton taille="atelier" bloc icone="camera" onClick={() => setActive(!active)}>
        {active ? 'Arrêter la caméra' : 'Lire le QR d’une étiquette'}
      </Bouton>
    </div>
  )
}
