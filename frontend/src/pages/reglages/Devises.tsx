/**
 * Réglages › Devises (`/reglages?onglet=devises`) : le cours de chaque devise (MAD pour une unité),
 * daté et gardé à chaque changement — un cours n'est écrit que si **le taux** change (P8-12). La
 * direction et les achats écrivent ; le dirham reste à 1. Le brouillon (cours tapés, devise à
 * demi saisie) vit dans la page Réglages : changer d'onglet ne le perd pas (P8-8).
 */
import { useState } from 'react'

import { Carte } from '../../composants/mise-en-page/Carte'
import { Grille } from '../../composants/mise-en-page/Grille'
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { Bouton } from '../../composants/saisie/Bouton'
import { Champ } from '../../composants/saisie/Champ'
import { lireNombre } from '../../composants/saisie/Nombre'
import { Saisie } from '../../composants/saisie/Saisie'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { api } from '../../lib/api'
import { cours as coursLisible, horodatage } from '../../lib/format'
import { useEcriture } from '../../lib/requetes'
import type { Schema } from '../../lib/types'
import { CoursDevise } from './CoursDevise'
import styles from './reglages.module.css'

export type DeviseFiche = Schema<'DeviseFiche'>

export interface SaisieDevise {
  nom: string
  cours: string
  actif: boolean
}

export interface BrouillonDevises {
  lignes: Readonly<Record<string, SaisieDevise>>
  nouvelle: { code: string; nom: string; cours: string }
}

export const BROUILLON_DEVISES_VIDE: BrouillonDevises = {
  lignes: {},
  nouvelle: { code: '', nom: '', cours: '' },
}

/** Vrai si une saisie de devise n'est pas enregistrée. */
export const deviseSale = (b: BrouillonDevises) =>
  Object.keys(b.lignes).length > 0 || Boolean(b.nouvelle.code || b.nouvelle.nom || b.nouvelle.cours)

/** Ce que le serveur refuserait pour un cours (dit sur le bouton). */
export function refusCours(texte: string): string[] {
  const v = lireNombre(texte)
  if (v == null) return ['Un cours est un nombre (virgule pour les décimales).']
  if (v <= 0) return ['Le cours doit être supérieur à 0.']
  if (v > 10000) return ['Le cours ne dépasse pas 10 000 MAD.']
  return []
}

const saisieDe = (d: DeviseFiche): SaisieDevise => ({
  nom: d.nom,
  cours: String(d.cours).replace('.', ','),
  actif: d.actif,
})

interface LignesProps {
  b: BrouillonDevises
  onB: (b: BrouillonDevises) => void
  ecrit: boolean
  onHistorique: (d: DeviseFiche) => void
}

function Enregistrer({
  d,
  s,
  onB,
  b,
}: {
  d: DeviseFiche
  s: SaisieDevise
  onB: LignesProps['onB']
  b: BrouillonDevises
}) {
  const ecrire = useEcriture(() =>
    api.put<DeviseFiche>(`/devises/${d.code}`, {
      nom: s.nom.trim(),
      cours: lireNombre(s.cours) ?? 0,
      actif: s.actif,
      version: d.version,
    }),
  )
  const retirer = () => {
    const lignes = { ...b.lignes }
    delete lignes[d.code]
    onB({ ...b, lignes })
  }
  return (
    <span className={styles.rangee}>
      <Bouton
        taille="petit"
        variante="principal"
        blocages={d.code === 'MAD' ? [] : refusCours(s.cours)}
        onClick={async () => {
          const f = await ecrire.mutateAsync()
          retirer()
          dire(
            f.cours !== d.cours
              ? `Cours ${d.code} enregistré : ${coursLisible(f.cours)} MAD.`
              : `Devise ${d.code} enregistrée.`,
          )
        }}
      >
        Enregistrer
      </Bouton>
      <Bouton taille="petit" onClick={retirer}>
        Annuler
      </Bouton>
    </span>
  )
}

function DepuisLe({ d }: { d: DeviseFiche }) {
  if (d.code === 'MAD') return <span className={styles.note}>référence</span>
  if (d.cours_repris) {
    return (
      <span
        className={styles.note}
        title="Aucun changement depuis la mise en service : c’est le cours repris"
      >
        cours de la reprise
      </span>
    )
  }
  return <>{horodatage(d.cours_le)}</>
}

function colonnes({ b, onB, ecrit, onHistorique }: LignesProps): Colonne<DeviseFiche>[] {
  const saisie = (d: DeviseFiche) => b.lignes[d.code] ?? saisieDe(d)
  const changer = (d: DeviseFiche, champ: Partial<SaisieDevise>) =>
    onB({ ...b, lignes: { ...b.lignes, [d.code]: { ...saisie(d), ...champ } } })
  const fige = (d: DeviseFiche) => !ecrit || d.code === 'MAD'
  const texte = (d: DeviseFiche, champ: 'nom' | 'cours', desactive: boolean) => (
    <Saisie
      libelle={`${champ === 'nom' ? 'Nom' : 'Cours'} de ${d.code}`}
      valeur={saisie(d)[champ]}
      desactive={desactive}
      max={champ === 'nom' ? 80 : 16}
      className={champ === 'cours' ? styles.nombre : undefined}
      onChange={(v) => changer(d, { [champ]: v })}
    />
  )
  const geste = (d: DeviseFiche) =>
    b.lignes[d.code] ? (
      <Enregistrer d={d} s={saisie(d)} onB={onB} b={b} />
    ) : (
      <Bouton
        taille="petit"
        titre="Les cours successifs de cette devise, qui les a saisis et quand"
        onClick={() => onHistorique(d)}
      >
        Historique
      </Bouton>
    )
  return [
    { cle: 'code', titre: 'Code', rendu: (d) => <span className={styles.code}>{d.code}</span> },
    { cle: 'nom', titre: 'Nom', rendu: (d) => texte(d, 'nom', !ecrit) },
    { cle: 'cours', titre: 'Cours (MAD)', droite: true, rendu: (d) => texte(d, 'cours', fige(d)) },
    { cle: 'cours_le', titre: 'Depuis le', rendu: (d) => <DepuisLe d={d} /> },
    {
      cle: 'actif',
      titre: 'Utilisée',
      rendu: (d) => (
        <input
          type="checkbox"
          aria-label={`${d.code} utilisée`}
          checked={saisie(d).actif}
          disabled={fige(d)}
          onChange={(e) => changer(d, { actif: e.target.checked })}
        />
      ),
    },
    { cle: 'gestes', titre: '', triable: false, exporte: false, rendu: geste },
  ]
}

function Ajout({
  b,
  onB,
  devises,
}: {
  b: BrouillonDevises
  onB: LignesProps['onB']
  devises: readonly DeviseFiche[]
}) {
  const n = b.nouvelle
  const code = n.code.trim().toUpperCase()
  const blocages = [
    ...(/^[A-Z]{3}$/.test(code) ? [] : ['Code de 3 lettres']),
    ...(n.cours ? refusCours(n.cours) : ['Cours > 0']),
    ...(devises.some((d) => d.code === code) ? ['Devise déjà connue'] : []),
  ]
  const ecrire = useEcriture(() =>
    api.post<DeviseFiche>('/devises', { code, nom: n.nom.trim(), cours: lireNombre(n.cours) ?? 0 }),
  )
  const poser = (champ: Partial<BrouillonDevises['nouvelle']>) => onB({ ...b, nouvelle: { ...n, ...champ } })
  return (
    <Carte titre="Ajouter une devise">
      <Grille colonnes={3}>
        <Champ libelle="Code (3 lettres)" aide="GBP, CNY, TRY…">
          <Saisie valeur={n.code} max={3} onChange={(v) => poser({ code: v.toUpperCase() })} />
        </Champ>
        <Champ libelle="Nom">
          <Saisie valeur={n.nom} max={80} onChange={(v) => poser({ nom: v })} />
        </Champ>
        <Champ libelle="Cours (MAD)" aide="combien de MAD pour une unité">
          <Saisie valeur={n.cours} max={16} className={styles.nombre} onChange={(v) => poser({ cours: v })} />
        </Champ>
      </Grille>
      <div className={styles.rangee}>
        <Bouton
          variante="principal"
          blocages={blocages}
          onClick={async () => {
            await ecrire.mutateAsync()
            onB({ ...b, nouvelle: BROUILLON_DEVISES_VIDE.nouvelle })
            dire(`Devise ${code} ajoutée.`)
          }}
        >
          Ajouter la devise
        </Bouton>
      </div>
    </Carte>
  )
}

export function Devises({
  devises,
  b,
  onB,
  ecrit,
}: {
  devises: readonly DeviseFiche[]
  b: BrouillonDevises
  onB: LignesProps['onB']
  ecrit: boolean
}) {
  const [historique, setHistorique] = useState<DeviseFiche | null>(null)
  return (
    <>
      <Carte titre="Cours de change" serre remplir className={styles.carteListe}>
        <Note>
          Le cours dit combien de MAD vaut une unité de la devise (1 EUR = 10,8 MAD, par exemple). Le MAD
          reste à 1. Chaque nouveau cours est daté et gardé : une commande garde le cours figé à la
          confirmation de ses prix, un dossier d’importation celui de la banque.
        </Note>
        <DataTable<DeviseFiche>
          libelle="Devises"
          lignes={devises}
          colonnes={colonnes({ b, onB, ecrit, onHistorique: setHistorique })}
          cle={(d) => d.code}
          recherche={false}
          triInitial={{ cle: 'code', sens: 1 }}
          vide="Aucune devise."
        />
      </Carte>
      {ecrit ? <Ajout b={b} onB={onB} devises={devises} /> : null}
      {historique ? <CoursDevise devise={historique} onFermer={() => setHistorique(null)} /> : null}
    </>
  )
}
