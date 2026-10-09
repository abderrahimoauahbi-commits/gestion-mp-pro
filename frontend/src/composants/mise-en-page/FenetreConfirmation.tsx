/**
 * La confirmation qui demande une **lecture longue** (A3) : restauration d'une sauvegarde,
 * clôture d'un dossier avec ses alertes, clôture de période. Tout autre geste se confirme sur la
 * ligne (`Confirmer`). Le motif s'y saisit quand il est demandé (`motifMin` : sa longueur la plus
 * courte) ; `caseJaiCompris` exige de cocher « J'ai compris » avant que le bouton s'active ; `mot`
 * exige de taper un mot (« RESTAURER »). Le bouton grisé dit pourquoi ; pendant l'envoi il est
 * occupé ; un refus est dit, la fenêtre reste ouverte ; réussi, elle se ferme.
 *
 * **Étapes** (`etapes`) : des lectures qui précèdent la dernière, chacune avec « Continuer » (et sa
 * case « J'ai compris » s'il y a lieu). **Issue** (`issue`, avec `fermerApres={false}`) : ce que la
 * fenêtre montre une fois la confirmation partie, quand l'opération se suit sur place (restauration) ;
 * tant que l'issue n'est pas `fermable`, la fenêtre ne se ferme pas.
 */
import { useState, type ReactNode } from 'react'

import { Bouton } from '../saisie/Bouton'
import { Champ } from '../saisie/Champ'
import { manqueMotif } from '../saisie/Confirmer'
import { Saisie } from '../saisie/Saisie'
import { Zone } from '../saisie/Zone'
import { Fenetre, useFermerFenetre } from './Fenetre'
import styles from './FenetreConfirmation.module.css'

/** Une lecture qui précède la dernière étape. */
export interface EtapeLecture {
  texte: ReactNode
  /** La case à cocher avant « Continuer ». */
  caseJaiCompris?: string
}

export interface FenetreConfirmationProps {
  titre: string
  texte: ReactNode
  /** Le libellé du bouton qui confirme (« Restaurer cette sauvegarde »). */
  oui: string
  /** Le motif tapé, et le mot tapé quand `mot` est demandé. */
  onOui: (motif: string, mot?: string) => unknown
  onFermer: () => void
  motif?: 'facultatif' | 'exige'
  /** La longueur la plus courte du motif exigé (celle du serveur) ; 1 par défaut. */
  motifMin?: number
  /** La longueur la plus longue du motif (celle du serveur) ; 500 par défaut. */
  motifMax?: number
  /** L'aide sous le motif (« écrit au journal des actions »). */
  aideMotif?: string
  /** Le texte de la case à cocher (« J'ai compris : les données actuelles seront remplacées. »). */
  caseJaiCompris?: string
  /** Le mot à taper avant de confirmer (« RESTAURER ») ; la casse ne compte pas. */
  mot?: string
  /** Les lectures qui précèdent la dernière étape. */
  etapes?: readonly EtapeLecture[]
  /** Faux : la fenêtre reste ouverte après la confirmation (l'appelant pose `issue`). */
  fermerApres?: boolean
  /** Ce que la fenêtre montre après la confirmation ; non `fermable`, elle ne se ferme pas. */
  issue?: { corps: ReactNode; fermable: boolean } | null
  variante?: 'principal' | 'danger'
}

const COCHER = 'Cochez « J’ai compris » pour continuer.'

interface Saisies {
  motif: string
  setMotif: (v: string) => void
  motTape: string
  setMotTape: (v: string) => void
  compris: boolean
  setCompris: (c: boolean) => void
}

function Annuler() {
  const fermer = useFermerFenetre()
  return <Bouton onClick={fermer}>Annuler</Bouton>
}

/** La case « J'ai compris ». */
function Compris({ texte, s }: { texte: string; s: Saisies }) {
  return (
    <label className={styles.compris}>
      <input type="checkbox" checked={s.compris} onChange={(e) => s.setCompris(e.target.checked)} />
      <span>{texte}</span>
    </label>
  )
}

/** Ce qui manque à la dernière étape : le mot, le motif. */
function manqueDerniere(p: FenetreConfirmationProps, s: Saisies): string[] {
  return [
    ...(p.mot && s.motTape.trim().toUpperCase() !== p.mot.toUpperCase() ? [`le mot ${p.mot}`] : []),
    ...(p.motif === 'exige' ? manqueMotif(s.motif, p.motifMin) : []),
  ]
}

/** Le corps de la dernière étape : le texte, le mot, le motif, la case. */
function Derniere({ p, s }: { p: FenetreConfirmationProps; s: Saisies }) {
  return (
    <>
      <div className={styles.texte}>{p.texte}</div>
      {p.mot ? (
        <Champ libelle={`Taper ${p.mot}`} obligatoire>
          <Saisie valeur={s.motTape} max={40} onChange={s.setMotTape} autoFocus />
        </Champ>
      ) : null}
      {p.motif ? (
        <Champ
          libelle={p.motif === 'exige' ? 'Motif' : 'Motif (facultatif)'}
          aide={p.aideMotif}
          obligatoire={p.motif === 'exige'}
        >
          <Zone valeur={s.motif} onChange={s.setMotif} max={p.motifMax ?? 500} />
        </Champ>
      ) : null}
      {p.caseJaiCompris ? <Compris texte={p.caseJaiCompris} s={s} /> : null}
    </>
  )
}

/** Le pied d'une étape : « Continuer » pour une lecture, le bouton qui confirme pour la dernière. */
function Pied({
  p,
  s,
  lecture,
  suite,
}: {
  p: FenetreConfirmationProps
  s: Saisies
  lecture?: EtapeLecture
  suite: () => void
}) {
  if (lecture)
    return (
      <>
        <Annuler />
        <Bouton
          variante="principal"
          grise={lecture.caseJaiCompris && !s.compris ? COCHER : undefined}
          onClick={suite}
        >
          Continuer
        </Bouton>
      </>
    )
  return (
    <>
      <Annuler />
      <Bouton
        variante={p.variante ?? 'principal'}
        manque={manqueDerniere(p, s)}
        grise={p.caseJaiCompris && !s.compris ? COCHER : undefined}
        attente="Envoi…"
        onClick={async () => {
          await (p.mot ? p.onOui(s.motif.trim(), s.motTape.trim()) : p.onOui(s.motif.trim()))
          if (p.fermerApres !== false) p.onFermer()
        }}
      >
        {p.oui}
      </Bouton>
    </>
  )
}

export function FenetreConfirmation(props: FenetreConfirmationProps) {
  const { titre, onFermer, etapes = [], issue } = props
  const [rang, setRang] = useState(0)
  const [motif, setMotif] = useState('')
  const [motTape, setMotTape] = useState('')
  const [compris, setCompris] = useState(false)
  const s: Saisies = { motif, setMotif, motTape, setMotTape, compris, setCompris }
  const lecture = etapes[rang]
  const suite = () => {
    setRang(rang + 1)
    setCompris(false)
  }
  if (issue)
    return (
      <Fenetre
        titre={titre}
        onFermer={issue.fermable ? onFermer : () => undefined}
        pied={
          issue.fermable ? (
            <Bouton variante="principal" onClick={onFermer}>
              Fermer
            </Bouton>
          ) : undefined
        }
      >
        {issue.corps}
      </Fenetre>
    )
  return (
    <Fenetre
      titre={titre}
      onFermer={onFermer}
      sale={Boolean(motif.trim() || motTape.trim())}
      pied={<Pied p={props} s={s} lecture={lecture} suite={suite} />}
    >
      {lecture ? (
        <>
          <div className={styles.texte}>{lecture.texte}</div>
          {lecture.caseJaiCompris ? <Compris texte={lecture.caseJaiCompris} s={s} /> : null}
        </>
      ) : (
        <Derniere p={props} s={s} />
      )}
    </Fenetre>
  )
}
