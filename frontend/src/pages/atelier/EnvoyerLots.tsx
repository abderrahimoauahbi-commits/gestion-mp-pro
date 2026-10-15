/**
 * Envoyer aux machines, étape 2 « Lots à prendre » : la demande rappelée, les fils (vue repliée :
 * les fils conformes regroupés « tout est conforme », (e)), un fil ajouté à la main, puis le
 * résumé collant avec « Valider la sortie » ; « Garder en brouillon » et « Abandonner » dessous.
 */
import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { BandeauBlocages } from '../../composants/atelier/BandeauBlocages'
import { EcranAtelier } from '../../composants/atelier/EcranAtelier'
import { ResumeValidation } from '../../composants/atelier/ResumeValidation'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { Confirmer } from '../../composants/saisie/Confirmer'
import { Selecteur } from '../../composants/saisie/Selecteur'
import { kgEtMetres, nombre } from '../../lib/format'
import { filConforme, priseDuSolde, type Fil } from '../../lib/ordre'
import { useLecture } from '../../lib/requetes'
import { fondsLaisses } from '../stock/fondsProposes'
import { enHaut, Fiche, NoteAtelier } from './briques'
import { dateLisible, qte, useMagasins, useNomMetier } from './commun'
import { useEmpechements } from './empechements'
import styles from './atelier.module.css'
import { EcartFil, FilCarte } from './FilCarte'
import type { OrdreFiche, QualiteResume } from './types'
import type { SaisieSortie } from './useSaisieSortie'

/** « Le 08/10/2026 (aujourd'hui) · Atelier · M1 · Van de Wiele n° 1 » : rappelé là où l'on valide. */
function useOu(s: SaisieSortie): string {
  const magasins = useMagasins()
  const nomMetier = useNomMetier()
  const magasin = magasins.data?.find((m) => m.id === s.magasin)?.code
  return [dateLisible(s.e.jour), magasin, nomMetier(s.e.metier)].filter(Boolean).join(' · ')
}

function Demande({ s, ou }: { s: SaisieSortie; ou: string }) {
  const qualites = useLecture<QualiteResume[]>('/qualites')
  const code = (id: number | null) => qualites.data?.find((q) => q.id === id)?.code ?? ''
  const resume = s.e.horsRecette
    ? 'Ordre hors recette'
    : s.e.fabrications.map((f) => `${code(f.qualite_id)} ${nombre(f.m2 ?? 0)} m²`).join(' · ')
  return (
    <Fiche titre={resume}>
      <NoteAtelier>
        Le {ou}
        {s.e.commentaire ? ` · ${s.e.commentaire}` : ''}
      </NoteAtelier>
      <Bouton taille="atelier" onClick={() => s.poser({ etape: 'demande' })}>
        Modifier la demande
      </Bouton>
    </Fiche>
  )
}

/** Les fils conformes repliés en une carte ; les autres ouverts. */
function Fils({ s }: { s: SaisieSortie }) {
  const [deplie, setDeplie] = useState(false)
  const conformes = s.fils.filter((f) => filConforme(f, s.dispo))
  const autres = s.fils.filter((f) => !conformes.includes(f))
  const total = conformes.reduce((t, f) => t + f.sorti, 0)
  const titre = !autres.length
    ? `Tout est conforme : ${nombre(conformes.length)} fils, ${qte(total)}`
    : `${nombre(conformes.length)} fil(s) conforme(s) — tout est conforme`
  return (
    <>
      {autres.map((f) => (
        <FilCarte key={f.matiere_id} s={s} f={f} />
      ))}
      {conformes.length ? (
        <Fiche ton="ok" libelle="Fils conformes">
          <Bouton taille="atelier" variante="fantome" bloc onClick={() => setDeplie(!deplie)}>
            {deplie ? `Replier : ${titre}` : titre}
          </Bouton>
          {deplie ? conformes.map((f: Fil) => <FilCarte key={f.matiere_id} s={s} f={f} />) : null}
        </Fiche>
      ) : null}
    </>
  )
}

function AjouterFil({ s }: { s: SaisieSortie }) {
  const pris = new Set(s.e.prises.map((p) => p.lot_id))
  const options = s.soldes
    .map((x) => ({ x, dispo: x.magasins.find((m) => m.magasin_id === s.magasin)?.quantite ?? 0 }))
    .filter(({ x, dispo }) => dispo > 0 && !pris.has(x.lot_id))
    .map(({ x, dispo }) => ({
      id: x.lot_id,
      titre: `${x.reference} · lot ${x.lot}`,
      sous: kgEtMetres(dispo, x.kg_par_ml, true),
      recherche: x.designation,
    }))
  return (
    <Fiche>
      <Champ libelle={s.e.horsRecette ? 'Ajouter un fil' : 'Ajouter un fil hors recette'}>
        <Selecteur
          valeur={null}
          placeholder="Référence ou numéro de lot…"
          options={options}
          onChange={(id) => {
            const x = s.soldes.find((l) => l.lot_id === id)
            if (x) s.poser({ prises: [...s.e.prises, priseDuSolde(x)] })
          }}
        />
      </Champ>
    </Fiche>
  )
}

function raisonValider(s: SaisieSortie, empechements: readonly string[]): string {
  if (empechements.length) return 'Validation impossible pour l’instant (voir le bandeau en tête)'
  if (s.depassements.length) return `${nombre(s.depassements.length)} lot(s) : plus que ce qu’ils portent`
  return ''
}

function PiedLots({ s, ou, raison, fin }: { s: SaisieSortie; ou: string; raison: string; fin: Fin }) {
  const lignes: [string, ReactNode][] = [['Total à sortir', <strong key="t">{qte(s.totalSorti)}</strong>]]
  if (s.totalPrevu)
    lignes.push(['Écart', <EcartFil key="e" ecart={s.totalSorti - s.totalPrevu} prevu={s.totalPrevu} />])
  return (
    <ResumeValidation lignes={lignes}>
      <Confirmer
        taille="atelier"
        variante="principal"
        manque={s.manqueBrouillon}
        grise={raison || undefined}
        question={`Sortir ${qte(s.totalSorti)} le ${ou} ? Le stock est débité tout de suite.`}
        oui="Oui, valider la sortie"
        attente="Enregistrement…"
        onOui={async () => fin(await s.enregistrer(true))}
      >
        Valider la sortie
      </Confirmer>
    </ResumeValidation>
  )
}

type Fin = (o: OrdreFiche | undefined) => void

function GestesBas({ s, fin }: { s: SaisieSortie; fin: Fin }) {
  const naviguer = useNavigate()
  return (
    <>
      <Bouton
        taille="atelier"
        bloc
        manque={s.manqueBrouillon}
        attente="Enregistrement…"
        onClick={async () => fin(await s.enregistrer(false))}
      >
        Garder en brouillon (sans sortir le stock)
      </Bouton>
      {s.e.id == null && (s.e.prises.length || s.repris) ? (
        <Confirmer
          taille="atelier"
          variante="danger"
          question="Abandonner cette sortie ? Rien n’est enregistré."
          oui="Oui, abandonner"
          onOui={() => {
            s.abandonner()
            void naviguer('/atelier')
          }}
        >
          Abandonner cette sortie
        </Confirmer>
      ) : null}
    </>
  )
}

export function EnvoyerLots({ s, onFait }: { s: SaisieSortie; onFait: (o: OrdreFiche) => void }) {
  useEffect(enHaut, [])
  const ou = useOu(s)
  const empechements = useEmpechements(s)
  const fin: Fin = (o) => {
    if (o) onFait(o)
  }
  const pied = <PiedLots s={s} ou={ou} raison={raisonValider(s, empechements)} fin={fin} />
  return (
    <EcranAtelier titre="Lots à prendre" enTete={<BandeauBlocages blocages={empechements} />} pied={pied}>
      <div className={styles.pile}>
        <Demande s={s} ou={ou} />
        {s.e.incompletes.length ? (
          <Note ton="critique">
            <strong>Recettes incomplètes</strong>
            {s.e.incompletes.map((x) => (
              <div key={x}>Recette incomplète — {x}</div>
            ))}
          </Note>
        ) : null}
        {fondsLaisses(s.e.besoins).length ? (
          <Note ton="attention">
            Fonds de lot laissés en stock (pas proposés) : {fondsLaisses(s.e.besoins).join(' · ')}. À mettre
            au rebut depuis la fiche du lot.
          </Note>
        ) : null}
        {!s.e.horsRecette ? (
          <NoteAtelier>
            Les quantités proposées suivent la recette, perte matière comprise (le taux des réglages, comme
            dans Production & besoins), et prennent les lots du plus ancien au plus récent. Corrigez au réel
            avant de valider.
          </NoteAtelier>
        ) : null}
        <Fils s={s} />
        <AjouterFil s={s} />
        {s.erreur ? <Note ton="critique">{s.erreur}</Note> : null}
        <GestesBas s={s} fin={fin} />
      </div>
    </EcranAtelier>
  )
}
