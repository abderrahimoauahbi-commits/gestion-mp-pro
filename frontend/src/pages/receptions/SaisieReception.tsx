/**
 * Nouvelle réception (`/receptions/nouvelle`) et « Corriger la réception » d'un brouillon
 * (`?brouillon=ID`), ECRANS-PRO 4.16 : la saisie d'un camion en fenêtre très large. Enregistrer
 * crée un brouillon — un par devise du camion, en **une** requête : tout ou rien — et ne fait rien
 * entrer en stock ; la validation viendra ensuite, depuis la fiche.
 */
import { useState, type SyntheticEvent } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Blocages } from '../../composants/saisie/Blocages'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { api } from '../../lib/api'
import { AIDE_ECRANS } from '../../lib/aide'
import { date, kg, part } from '../../lib/format'
import { aujourdhui } from '../../lib/heure'
import { useEcriture } from '../../lib/requetes'
import styles from '../plan-achat/achats.module.css'
import { blocagesSaisie, corps, devisesDuCamion, totaux, type Tolerances } from './calculSaisie'
import { useBons, useFournisseursActifs, useMagasins, useMatieresActives, useReception } from './donnees'
import { EnTeteSaisie, FacturesSaisie } from './EnTeteSaisie'
import { TableSaisie } from './TableSaisie'
import { useTolerances } from './tolerances'
import type { ReceptionFiche } from './types'
import { useSaisieReception, type Referentiels, type SaisieReception as Saisie } from './useSaisieReception'

const CLE_AIDE = 'gestion-mp-pro.aide-reception'

/** Le mode d'emploi s'ouvre la toute première fois, puis reste replié (sauf si on le rouvre). */
function lireAide(): boolean {
  try {
    const etat = localStorage.getItem(CLE_AIDE)
    if (etat == null) localStorage.setItem(CLE_AIDE, 'repliee')
    return etat == null || etat === 'ouverte'
  } catch {
    return false
  }
}

function ModeEmploi() {
  const [ouvert, setOuvert] = useState(lireAide)
  const basculer = (e: SyntheticEvent<HTMLDetailsElement>) => {
    const o = e.currentTarget.open
    setOuvert(o)
    try {
      localStorage.setItem(CLE_AIDE, o ? 'ouverte' : 'repliee')
    } catch {
      /* navigateur sans stockage : rien à retenir */
    }
  }
  return (
    <details className={styles.repli} open={ouvert} onToggle={basculer}>
      <summary>Mode d’emploi</summary>
      <ol className={styles.liste}>
        {(AIDE_ECRANS.reception_saisie?.points ?? []).map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ol>
    </details>
  )
}

/** Ce qui manque pour enregistrer (le bouton le dit). */
export function manquesSaisie(
  s: Pick<Saisie, 'fournisseurId' | 'lignes' | 'entete'>,
  correction: boolean,
): string[] {
  const m: string[] = []
  if (!s.fournisseurId) m.push('le fournisseur (ou le n° du bon)')
  if (!s.lignes.length)
    m.push('au moins une ligne : cochez un bon de commande, ou ajoutez une matière hors commande')
  if (s.entete.date > aujourdhui()) m.push('une date d’arrivée qui n’est pas dans le futur')
  if (correction && devisesDuCamion(s.lignes).length > 1)
    m.push('une seule devise (un brouillon ne mêle pas deux devises)')
  return m
}

function Pied({
  s,
  r,
  tol,
  onEnregistrees,
}: {
  s: Saisie
  r: ReceptionFiche | null
  tol: Tolerances
  onEnregistrees: (l: ReceptionFiche[]) => void
}) {
  const fermer = useFermerFenetre()
  const enregistrer = useEcriture(async () => {
    if (!s.fournisseurId) return []
    const c = corps({ fournisseurId: s.fournisseurId, ...s.entete }, s.lignes, s.factures)
    return r
      ? [await api.put<ReceptionFiche>(`/receptions/${r.id}`, { ...c, version: r.version })]
      : await api.post<ReceptionFiche[]>('/receptions', c)
  })
  const t = totaux(s.lignes, tol)
  return (
    <div className={styles.pied}>
      <span className={styles.note}>
        {r ? `Brouillon saisi par ${r.cree_par || '—'}, arrivée du ${date(r.date)}. ` : ''}
        Enregistrer ne fait rien entrer en stock : la validation viendra ensuite. {s.lignes.length} ligne(s) ·{' '}
        {kg(t.pese)} pesés.
        {t.horsTolerance ? (
          <strong>
            {' '}
            {t.horsTolerance} écart(s) de pesée au-delà de {part(tol.pesee, 0)} : vérifiez la bascule et le
            BL, notez-le en observation.
          </strong>
        ) : null}
      </span>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Annuler</Bouton>
      <Bouton
        variante="principal"
        attente="Enregistrement…"
        manque={manquesSaisie(s, Boolean(r))}
        titre="Enregistre en brouillon : rien n’entre en stock avant la validation"
        onClick={async () => onEnregistrees(await enregistrer.mutateAsync())}
      >
        {r ? 'Enregistrer les corrections' : 'Enregistrer le brouillon'}
      </Bouton>
    </div>
  )
}

function Question({ s }: { s: Saisie }) {
  if (!s.question) return null
  const q = s.question
  return (
    <div className={styles.panneau} role="alert">
      <span>{q.texte}</span>
      <span className={styles.rangeeCentree}>
        <Bouton onClick={s.fermerQuestion}>Non</Bouton>
        <Bouton
          variante="danger"
          onClick={() => {
            q.faire()
            s.fermerQuestion()
          }}
        >
          {q.oui}
        </Bouton>
      </span>
    </div>
  )
}

function Formulaire({
  r,
  donnees,
  onFermer,
  onEnregistrees,
}: {
  r: ReceptionFiche | null
  donnees: Referentiels
  onFermer: () => void
  onEnregistrees: (l: ReceptionFiche[]) => void
}) {
  const s = useSaisieReception(r, donnees)
  const tol = useTolerances()
  const blocages = blocagesSaisie(s.lignes, donnees.magasins, tol)
  return (
    <Fenetre
      titre={r ? `Corriger la réception — ${r.numero ?? 'Brouillon'}` : 'Nouvelle réception'}
      taille="tresLarge"
      sale={s.sale}
      onFermer={onFermer}
      pied={<Pied s={s} r={r} tol={tol} onEnregistrees={onEnregistrees} />}
    >
      <EnTeteSaisie s={s} donnees={donnees} />
      <div className={styles.replis}>
        <ModeEmploi />
        {s.fournisseur ? <FacturesSaisie s={s} /> : null}
        {blocages.length ? (
          <details className={styles.repli}>
            <summary className={styles.attention}>
              Sera refusé à la validation : {blocages.length} point(s) à régler
            </summary>
            <Blocages blocages={blocages} titre="Sera refusé à la validation :" />
          </details>
        ) : null}
      </div>
      <Question s={s} />
      {s.fournisseur ? (
        <TableSaisie
          lignes={s.lignes}
          tol={tol}
          magasins={donnees.magasins}
          devises={[...new Set(donnees.matieres.map((m) => m.devise ?? 'MAD'))].sort()}
          modifier={s.modifier}
          retirer={s.retirer}
          ajouterLot={s.ajouterLot}
        />
      ) : (
        <Note>Choisissez d’abord le fournisseur, ou tapez le n° du bon que le chauffeur apporte.</Note>
      )}
    </Fenetre>
  )
}

export function SaisieReception({
  brouillon,
  onFermer,
  onEnregistrees,
}: {
  brouillon: number | null
  onFermer: () => void
  onEnregistrees: (l: ReceptionFiche[]) => void
}) {
  const fournisseurs = useFournisseursActifs()
  const bons = useBons()
  const matieres = useMatieresActives()
  const magasins = useMagasins()
  const fiche = useReception(brouillon)
  const lectures = [fournisseurs, bons, matieres, magasins, ...(brouillon ? [fiche] : [])]
  const erreur = lectures.find((l) => l.isError)?.error
  if (erreur || lectures.some((l) => !l.data))
    return (
      <Fenetre
        titre={brouillon ? 'Corriger la réception' : 'Nouvelle réception'}
        taille="tresLarge"
        onFermer={onFermer}
      >
        {erreur ? (
          <Erreur erreur={erreur} />
        ) : (
          <Chargement quoi="les fournisseurs, les bons et les magasins" />
        )}
      </Fenetre>
    )
  if (fiche.data && fiche.data.statut !== 'brouillon')
    return (
      <Fenetre titre="Corriger la réception" onFermer={onFermer}>
        <Note ton="attention">
          La réception {fiche.data.numero ?? ''} vient d’être validée ou annulée : elle ne se corrige plus.
        </Note>
      </Fenetre>
    )
  const donnees: Referentiels = {
    fournisseurs: fournisseurs.data ?? [],
    bons: bons.data ?? [],
    matieres: matieres.data ?? [],
    magasins: magasins.data ?? [],
  }
  return (
    <Formulaire
      r={brouillon ? (fiche.data ?? null) : null}
      donnees={donnees}
      onFermer={onFermer}
      onEnregistrees={onEnregistrees}
    />
  )
}
