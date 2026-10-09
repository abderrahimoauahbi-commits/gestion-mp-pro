/**
 * Les choix du périmètre d'un inventaire (ECRANS-PRO partie 6) : famille (rôles, compositions,
 * classes ABC — critères cumulés), certaines matières (en stock dans le magasin choisi, an. 17),
 * tournant (matières dues, décochables).
 */
import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'

import { Champ } from '../../composants/saisie/Champ'
import { Bouton } from '../../composants/saisie/Bouton'
import { SelecteurMatiere } from '../../composants/saisie/SelecteurMatiere'
import type { Colonne } from '../../composants/tableaux/colonnes'
import { DataTable } from '../../composants/tableaux/DataTable'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Note } from '../../composants/retour/Note'
import type { ErreurApi } from '../../lib/api'
import { date, kgEtMetres, VIDE } from '../../lib/format'
import styles from './Inventaire.module.css'
import { choixMatiere } from './matieres'
import type { DefautsInventaire, MatiereACompter, MatiereResume } from './types'

/** Des cases à cocher (plusieurs choix) ; « — » s'il n'y a rien à cocher. */
export function Cases<K extends string | number>({
  libelle,
  options,
  valeurs,
  onChange,
}: {
  libelle: string
  options: readonly { id: K; libelle: string; titre?: string }[]
  valeurs: readonly K[]
  onChange: (valeurs: K[]) => void
}) {
  return (
    <Champ libelle={libelle} groupe>
      <div className={styles.cases} role="group" aria-label={libelle}>
        {options.length
          ? options.map((o) => (
              <label key={o.id} title={o.titre}>
                <input
                  type="checkbox"
                  checked={valeurs.includes(o.id)}
                  onChange={(e) =>
                    onChange(e.target.checked ? [...valeurs, o.id] : valeurs.filter((v) => v !== o.id))
                  }
                />
                {o.libelle}
              </label>
            ))
          : VIDE}
      </div>
    </Champ>
  )
}

const CLASSES = [
  { id: 'A', libelle: 'Classe A', titre: 'A : l’essentiel de la valeur consommée' },
  { id: 'B', libelle: 'Classe B' },
  { id: 'C', libelle: 'Classe C' },
]

export function ParFamille(p: {
  defauts: DefautsInventaire
  roles: readonly number[]
  compositions: readonly number[]
  classes: readonly string[]
  poser: (modif: { roles?: number[]; compositions?: number[]; classes?: string[] }) => void
}) {
  return (
    <>
      <Cases
        libelle="Rôles"
        options={p.defauts.roles.map((r) => ({ id: r.id, libelle: r.code }))}
        valeurs={p.roles}
        onChange={(roles) => p.poser({ roles })}
      />
      <Cases
        libelle="Compositions"
        options={p.defauts.compositions.map((c) => ({ id: c.id, libelle: c.code }))}
        valeurs={p.compositions}
        onChange={(compositions) => p.poser({ compositions })}
      />
      <Cases
        libelle="Classes ABC"
        options={CLASSES}
        valeurs={p.classes}
        onChange={(classes) => p.poser({ classes })}
      />
      <Note>Une matière est comptée si elle passe tous les critères cochés.</Note>
    </>
  )
}

export function CertainesMatieres(p: {
  enStock: readonly MatiereResume[]
  choisies: readonly number[]
  stockDe: (id: number) => number
  poser: (matieres: number[]) => void
}) {
  const proposees = p.enStock.filter((m) => !p.choisies.includes(m.id))
  return (
    <>
      <Champ
        libelle="Ajouter une matière à compter"
        groupe
        aide="Les matières en stock dans le magasin choisi"
      >
        <SelecteurMatiere
          libelle="Ajouter une matière à compter"
          matieres={proposees.map(choixMatiere)}
          valeur={null}
          onChange={(id) => (id == null ? undefined : p.poser([...p.choisies, id]))}
        />
      </Champ>
      <div className={styles.puces} aria-label="Matières choisies">
        {p.choisies.length
          ? p.choisies.map((id) => {
              const m = p.enStock.find((x) => x.id === id)
              const ref = m?.reference ?? `n° ${id}`
              return (
                <Bouton
                  key={id}
                  taille="petit"
                  titre={`Retirer ${ref} (${kgEtMetres(p.stockDe(id), m?.kg_par_ml)} en stock)`}
                  onClick={() => p.poser(p.choisies.filter((x) => x !== id))}
                >
                  {ref} ×
                </Bouton>
              )
            })
          : 'Aucune matière choisie.'}
      </div>
    </>
  )
}

type CD = Colonne<MatiereACompter>

function colonnesDues(ecartees: readonly number[], basculer: (id: number) => void): CD[] {
  const eteinte = (d: MatiereACompter, contenu: ReactNode) =>
    ecartees.includes(d.article_id) ? <span className={styles.eteinte}>{contenu}</span> : contenu
  return [
    {
      cle: 'case',
      titre: 'Compter',
      triable: false,
      valeur: (d) => (ecartees.includes(d.article_id) ? 0 : 1),
      rendu: (d) => (
        <input
          type="checkbox"
          aria-label={`Compter ${d.reference}`}
          checked={!ecartees.includes(d.article_id)}
          onChange={() => basculer(d.article_id)}
        />
      ),
    },
    { cle: 'reference', titre: 'Référence', rendu: (d) => eteinte(d, <strong>{d.reference}</strong>) },
    { cle: 'role', titre: 'Rôle', rendu: (d) => eteinte(d, d.role) },
    { cle: 'classe_abc', titre: 'Classe', rendu: (d) => eteinte(d, d.classe_abc ?? VIDE) },
    {
      cle: 'stock',
      titre: 'Stock',
      droite: true,
      rendu: (d) => eteinte(d, kgEtMetres(d.stock, d.kg_par_ml)),
    },
    {
      cle: 'dernier',
      titre: 'Dernier comptage',
      aide: 'Un comptage vaut pour le magasin compté : la matière est due dans ces magasins',
      valeur: (d) => d.dernier_comptage,
      rendu: (d) =>
        eteinte(
          d,
          <span className={styles.valeur}>
            <span>
              {d.dernier_comptage ? `${date(d.dernier_comptage)} (il y a ${d.jours} j)` : 'jamais compté'}
            </span>
            <span className={styles.note}>{d.magasins.join(' · ')}</span>
          </span>,
        ),
    },
  ]
}

export function Tournant(p: {
  dues: UseQueryResult<MatiereACompter[], ErreurApi>
  ecartees: readonly number[]
  basculer: (id: number) => void
}) {
  const { dues } = p
  if (dues.isPending) return <Chargement quoi="les matières dues" />
  if (dues.isError) return <Erreur erreur={dues.error} onReessayer={() => void dues.refetch()} />
  return (
    <>
      <Note>
        Cadence : A tous les 30 jours, B tous les 90 jours, C tous les 365 jours ; une matière jamais comptée
        est due.
      </Note>
      <DataTable
        libelle="Matières dues"
        lignes={dues.data}
        colonnes={colonnesDues(p.ecartees, p.basculer)}
        cle={(d) => d.article_id}
        recherche={false}
        hauteur="fenetre"
        vide="Aucune matière n’est due : toutes ont été comptées à temps."
      />
    </>
  )
}
