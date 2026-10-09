/**
 * Les pièces jointes d'une fiche (commande, réception, réclamation, dossier, inventaire,
 * fournisseur, matière) : joindre (bouton ou glisser-déposer), télécharger, retirer (confirmé sur
 * place, retrait tracé). Types et taille annoncés et vérifiés **avant** l'envoi (20 Mo, pas de
 * SVG) ; un fichier après l'autre, liste relue après chacun, bilan « n joints, m refusés : … ».
 * L'alimentation ne voit jamais de pièce. `mode` : `complet` (joindre et retirer), `joindre`
 * (joindre seulement : un dossier clos s'enrichit, rien ne s'en retire), `lecture` (aucun geste) ;
 * `lectureSeule` vaut `mode="lecture"`.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useId, useRef, useState, type DragEvent } from 'react'

import { messageErreur, requete } from '../../lib/api'
import { horodatage, nombre } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import { Chargement } from '../retour/Chargement'
import { Erreur } from '../retour/Erreur'
import { dire } from '../retour/Messages'
import { Confirmer } from '../saisie/Confirmer'
import { DataTable } from '../tableaux/DataTable'
import type { Colonne } from '../tableaux/colonnes'
import styles from './PiecesJointes.module.css'

export type ObjetPiece =
  'commande' | 'reception' | 'reclamation' | 'dossier' | 'inventaire' | 'fournisseur' | 'matiere'

/** Une pièce jointe (type provisoire, remplacé par `Schema<'PieceFiche'>` à la publication). */
export interface PieceFiche {
  id: number
  nom: string
  genre: string
  taille: number
  par: string
  joint_le: string
}

/** 20 Mo au plus par fichier. */
export const TAILLE_MAX = 20 * 1024 * 1024
/** Les types acceptés : PDF, images « à points » (jamais de SVG), tableurs, textes, documents, zip. */
export const EXTENSIONS = [
  '.pdf',
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.heic',
  '.heif',
  '.tif',
  '.tiff',
  '.bmp',
  '.txt',
  '.csv',
  '.xlsx',
  '.xls',
  '.ods',
  '.docx',
  '.doc',
  '.odt',
  '.zip',
]

/** « 512 o », « 12,4 Ko », « 3,2 Mo ». */
export function tailleLisible(octets: number): string {
  if (octets < 1024) return `${nombre(octets)}\u00a0o`
  if (octets < 1024 * 1024) return `${nombre(octets / 1024, 0, 1)}\u00a0Ko`
  return `${nombre(octets / 1024 / 1024, 0, 1)}\u00a0Mo`
}

/** Pourquoi un fichier sera refusé avant l'envoi, ou ''. */
export function refusAvantEnvoi(f: { name: string; size: number }): string {
  const ext = f.name.toLowerCase().match(/\.[a-z0-9]+$/)?.[0] ?? ''
  if (!EXTENSIONS.includes(ext))
    return `« ${f.name} » : type de fichier refusé (PDF, image, tableur, texte ou document).`
  if (f.size > TAILLE_MAX) return `« ${f.name} » est trop lourd : 20 Mo au plus.`
  return ''
}

/** Joint les fichiers un par un, relit la liste après chacun, et dit le bilan. */
function useJoindre(objet: ObjetPiece, id: number) {
  const client = useQueryClient()
  const [envoi, setEnvoi] = useState(false)
  const joindre = async (fichiers: readonly File[]) => {
    if (!fichiers.length) return
    setEnvoi(true)
    const refus: string[] = []
    let joints = 0
    for (const f of fichiers) {
      const avant = refusAvantEnvoi(f)
      if (avant) {
        refus.push(avant)
        continue
      }
      const corps = new FormData()
      corps.append('objet', objet)
      corps.append('id', String(id))
      corps.append('fichier', f, f.name)
      try {
        await requete('/pieces', { methode: 'POST', corps })
        joints++
      } catch (e) {
        refus.push(`« ${f.name} » : ${messageErreur(e)}`)
      }
      await client.invalidateQueries({ queryKey: ['/pieces'] })
    }
    setEnvoi(false)
    const bilan = `${nombre(joints)} joint${joints > 1 ? 's' : ''}${refus.length ? `, ${nombre(refus.length)} refusé${refus.length > 1 ? 's' : ''} : ${refus.join(' ')}` : '.'}`
    dire(bilan, refus.length ? (joints ? 'attention' : 'erreur') : 'succes')
  }
  return { joindre, envoi }
}

function colonnes(sansRetrait: boolean, retirer: (p: PieceFiche) => Promise<unknown>): Colonne<PieceFiche>[] {
  const liste: Colonne<PieceFiche>[] = [
    {
      cle: 'nom',
      titre: 'Document',
      triable: false,
      rendu: (p) => (
        <a href={`/api/pieces/${p.id}/fichier`} title="Télécharger le document" download>
          {p.nom}
        </a>
      ),
    },
    { cle: 'genre', titre: 'Genre', triable: false },
    { cle: 'taille', titre: 'Taille', droite: true, triable: false, rendu: (p) => tailleLisible(p.taille) },
    { cle: 'par', titre: 'Par', triable: false },
    { cle: 'joint_le', titre: 'Joint le', triable: false, rendu: (p) => horodatage(p.joint_le) },
  ]
  if (sansRetrait) return liste
  return [
    ...liste,
    {
      cle: 'retirer',
      titre: '',
      triable: false,
      exporte: false,
      rendu: (p) => (
        <Confirmer
          taille="petit"
          variante="danger"
          question="Retirer ce document ?"
          oui="Oui, retirer"
          titre={`Retirer « ${p.nom} » de la liste (le retrait est tracé)`}
          onOui={() => retirer(p)}
        >
          Retirer
        </Confirmer>
      ),
    },
  ]
}

/** Le bouton « Joindre un document… » et ce qu'il accepte. */
function Joindre({ joindre, envoi }: { joindre: (f: readonly File[]) => Promise<void>; envoi: boolean }) {
  const champ = useRef<HTMLInputElement>(null)
  const idChamp = useId()
  return (
    <div className={styles.joindre}>
      <input
        ref={champ}
        id={idChamp}
        type="file"
        multiple
        hidden
        accept={EXTENSIONS.join(',')}
        onChange={(e) =>
          void joindre([...(e.target.files ?? [])]).finally(() => {
            if (champ.current) champ.current.value = ''
          })
        }
      />
      <label htmlFor={idChamp} className={styles.bouton} aria-disabled={envoi}>
        <Icone nom="piece" />
        {envoi ? 'Envoi…' : 'Joindre un document…'}
      </label>
      <span className={styles.note}>
        ou le glisser ici · PDF, image, tableur, texte ou document · 20 Mo au plus. Ouvrir un document le
        télécharge.
      </span>
    </div>
  )
}

export type ModePieces = 'complet' | 'joindre' | 'lecture'

export function PiecesJointes({
  objet,
  id,
  lectureSeule = false,
  mode = lectureSeule ? 'lecture' : 'complet',
}: {
  objet: ObjetPiece
  id: number
  lectureSeule?: boolean
  mode?: ModePieces
}) {
  const joindreCache = mode === 'lecture'
  const pieces = useLecture<PieceFiche[]>('/pieces', { objet, id })
  const { joindre, envoi } = useJoindre(objet, id)
  const [survol, setSurvol] = useState(false)
  const retirer = async (p: PieceFiche) => {
    await requete(`/pieces/${p.id}`, { methode: 'DELETE' })
    await pieces.refetch()
    dire(`« ${p.nom} » retiré.`)
  }
  const deposer = (e: DragEvent) => {
    e.preventDefault()
    setSurvol(false)
    if (!joindreCache) void joindre([...e.dataTransfer.files])
  }
  return (
    <div
      className={classes(styles.pieces, survol && !joindreCache && styles.survol)}
      onDragOver={(e) => {
        e.preventDefault()
        if (!joindreCache) setSurvol(true)
      }}
      onDragLeave={() => setSurvol(false)}
      onDrop={deposer}
    >
      {joindreCache ? null : <Joindre joindre={joindre} envoi={envoi} />}
      {pieces.isPending ? <Chargement quoi="les documents joints" /> : null}
      {pieces.isError ? <Erreur erreur={pieces.error} onReessayer={() => void pieces.refetch()} /> : null}
      {pieces.data ? (
        <DataTable
          lignes={pieces.data}
          colonnes={colonnes(mode !== 'complet', retirer)}
          cle={(p) => p.id}
          recherche={false}
          hauteur="fenetre"
          vide="Aucun document joint."
          libelle="Documents joints"
        />
      ) : null}
    </div>
  )
}
