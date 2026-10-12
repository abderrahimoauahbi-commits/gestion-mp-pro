/**
 * « Références arrivées » (ECRANS-PRO 4.16) : la fenêtre, grande et lisible, où l'on coche ce que le
 * camion a apporté parmi les lignes du bon qui restent à livrer. Seules les références cochées
 * entrent dans la saisie ; décocher une ligne déjà saisie (lot, pesée) le demande d'abord. Ce qui
 * n'est pas coché reste dû sur le bon, pour le camion suivant.
 */
import { useMemo, useState } from 'react'

import { Fenetre, useFermerFenetre } from '../../composants/mise-en-page/Fenetre'
import { Chargement } from '../../composants/retour/Chargement'
import { Erreur } from '../../composants/retour/Erreur'
import { Bouton } from '../../composants/saisie/Bouton'
import { Saisie } from '../../composants/saisie/Saisie'
import { kg, nombre, part } from '../../lib/format'
import { useLecture } from '../../lib/requetes'
import type { CommandeFiche, LigneCommande } from '../commandes/types'
import { nu } from '../importations/ChoixFacture'
import styles from './ChoixReferences.module.css'

/** Le reste en unités d'achat (palettes, cartons…), quand le bon en donne la contenance. */
function enUnites(l: LigneCommande): string {
  if (!l.contenance || !l.unite_achat || l.unite_achat === 'kg') return ''
  const n = l.reste / l.contenance
  return `≈ ${nombre(n, 0, 1)} ${l.unite_achat.toLowerCase()}${n >= 2 ? 's' : ''}`
}

function Ligne({
  l,
  coche,
  saisie,
  basculer,
}: {
  l: LigneCommande
  coche: boolean
  saisie: boolean
  basculer: () => void
}) {
  return (
    <tr className={coche ? styles.cochee : undefined} onClick={basculer}>
      <td className={styles.case}>
        <input
          type="checkbox"
          checked={coche}
          onChange={basculer}
          onClick={(e) => e.stopPropagation()}
          aria-label={`${l.reference} arrivée`}
        />
      </td>
      <td>
        <span className={styles.reference}>{l.reference}</span>
        {l.designation ? <span className={styles.designation}>{l.designation}</span> : null}
      </td>
      <td className={styles.nombre}>{kg(l.quantite)}</td>
      <td className={styles.nombre}>{l.recu ? kg(l.recu) : '—'}</td>
      <td className={styles.nombre}>
        <strong>{kg(l.reste)}</strong>
        <span className={styles.designation}>{enUnites(l)}</span>
      </td>
      <td className={styles.etat}>{saisie ? 'déjà saisie' : ''}</td>
    </tr>
  )
}

function Tableau({
  lignes,
  coches,
  saisies,
  basculer,
}: {
  lignes: readonly LigneCommande[]
  coches: ReadonlySet<number>
  saisies: ReadonlySet<number>
  basculer: (id: number) => void
}) {
  if (!lignes.length) return <p className={styles.vide}>Aucune référence ne correspond à la recherche.</p>
  return (
    <table className={styles.tableau} aria-label="Références du bon">
      <thead>
        <tr>
          <th className={styles.case} />
          <th>Référence</th>
          <th className={styles.nombre}>Commandé</th>
          <th className={styles.nombre}>Déjà reçu</th>
          <th className={styles.nombre}>Reste à livrer</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {lignes.map((l) => (
          <Ligne
            key={l.id}
            l={l}
            coche={coches.has(l.id)}
            saisie={saisies.has(l.id)}
            basculer={() => basculer(l.id)}
          />
        ))}
      </tbody>
    </table>
  )
}

export interface ChoixReferencesProps {
  /** Le bon dont on choisit les références. */
  commandeId: number
  /** Les lignes du bon déjà dans la saisie, et celles déjà saisies (lot, pesée). */
  dedans: ReadonlySet<number>
  saisies: ReadonlySet<number>
  /** Rend la fiche du bon et les lignes cochées. */
  onChoisir: (fiche: CommandeFiche, cochees: ReadonlySet<number>) => void
  onFermer: () => void
}

function Pied({ n, total, valider }: { n: number; total: number; valider: () => void }) {
  const fermer = useFermerFenetre()
  return (
    <div className={styles.pied}>
      <span className={styles.note}>
        {n} référence(s) cochée(s) sur {total} · ce qui n’est pas coché reste dû sur le bon.
      </span>
      <span className={styles.pousse} />
      <Bouton onClick={fermer}>Annuler</Bouton>
      <Bouton variante="principal" onClick={valider} manque={n ? undefined : ['au moins une référence']}>
        {`Prendre ${n} référence(s) dans la réception`}
      </Bouton>
    </div>
  )
}

function Contenu({ fiche, ...p }: ChoixReferencesProps & { fiche: CommandeFiche }) {
  const aLivrer = useMemo(
    () => fiche.lignes.filter((l) => l.reste > 0 || p.dedans.has(l.id)),
    [fiche.lignes, p.dedans],
  )
  const [coches, setCoches] = useState<Set<number>>(() => new Set(p.dedans))
  const [recherche, setRecherche] = useState('')
  const visibles = aLivrer.filter((l) => nu(`${l.reference} ${l.designation}`).includes(nu(recherche)))
  const basculer = (id: number) =>
    setCoches((c) => {
      const n = new Set(c)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  const tout = (oui: boolean) =>
    setCoches((c) => {
      const n = new Set(c)
      for (const l of visibles) {
        if (oui) n.add(l.id)
        else n.delete(l.id)
      }
      return n
    })
  return (
    <Fenetre
      titre={`Références arrivées — ${fiche.numero ?? 'bon'} · ${fiche.fournisseur}`}
      taille="tresLarge"
      onFermer={p.onFermer}
      pied={<Pied n={coches.size} total={aLivrer.length} valider={() => p.onChoisir(fiche, coches)} />}
    >
      <div className={styles.outils}>
        <Saisie
          valeur={recherche}
          onChange={setRecherche}
          placeholder="Chercher une référence, une couleur…"
          libelle="Chercher une référence"
        />
        <Bouton onClick={() => tout(true)}>Tout cocher</Bouton>
        <Bouton onClick={() => tout(false)}>Tout décocher</Bouton>
        <span className={styles.note}>
          {kg(fiche.reste_kg)} restent à livrer sur ce bon · {part(fiche.part_livree, 0)} déjà reçu. Cochez ce
          que le camion a apporté (un clic sur la ligne suffit).
        </span>
      </div>
      <Tableau lignes={visibles} coches={coches} saisies={p.saisies} basculer={basculer} />
    </Fenetre>
  )
}

export function ChoixReferences(p: ChoixReferencesProps) {
  const fiche = useLecture<CommandeFiche>(`/commandes/${p.commandeId}`)
  if (!fiche.data)
    return (
      <Fenetre titre="Références arrivées" taille="tresLarge" onFermer={p.onFermer}>
        {fiche.isError ? <Erreur erreur={fiche.error} /> : <Chargement quoi="les lignes du bon" />}
      </Fenetre>
    )
  return <Contenu {...p} fiche={fiche.data} />
}
