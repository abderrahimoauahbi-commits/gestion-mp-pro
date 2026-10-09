/**
 * La recette d'une qualité, groupée par rôle : une ligne de rôle (« Poil · 0,8000 kg/m² », en
 * rouge si ses parts ne font pas 100 %), puis ses matières — référence, fournisseur, part (saisie
 * par la direction), ml/m² et kg/m² calculés à la frappe comme le serveur, prix d'achat et coût
 * au m² (absents pour l'alimentation), autres qualités qui la portent, « Retirer ». Pied : toute
 * la recette.
 */
import { Cadre } from '../../composants/tableaux/Cadre'
import tableau from '../../composants/tableaux/DataTable.module.css'
import { Bouton } from '../../composants/saisie/Bouton'
import { Nombre } from '../../composants/saisie/Nombre'
import { nombre, prix, prixUnite, VIDE } from '../../lib/format'
import styles from '../catalogue/catalogue.module.css'
import type { GroupeRole, LigneCalculee } from './recette'

/** Ce que dit un rôle de son état. */
export function etatLisible(g: GroupeRole): string {
  if (g.etat === 'complet') return 'le rôle est complet'
  if (g.etat === 'vide') return 'aucune matière : en ajouter une ci-dessous'
  const ecart = nombre(Math.abs(g.somme - 100), 2)
  return g.etat === 'trop' ? `${ecart} % de trop` : `il manque ${ecart} %`
}

export interface TableRecetteProps {
  groupes: readonly GroupeRole[]
  voitPrix: boolean
  /** La direction saisit les parts et retire des matières. */
  ecrit: boolean
  /** Les autres qualités qui portent chaque matière. */
  autres: ReadonlyMap<number, readonly string[]>
  onPart: (matiere_id: number, part: number | null) => void
  onRetirer: (matiere_id: number) => void
}

function Ligne({ l, p, lineaire }: { l: LigneCalculee; p: TableRecetteProps; lineaire: boolean }) {
  const titreKg =
    lineaire && l.ml_m2 != null ? `${nombre(l.ml_m2, 4)} ml/m² × ${nombre(l.densite, 0, 6)} kg/ml` : undefined
  return (
    <tr>
      <td>
        <span className={styles.code}>{l.reference}</span>
        <span className={styles.dessous}>{[l.nature, l.designation].filter(Boolean).join(' · ')}</span>
      </td>
      <td>{l.fournisseur || VIDE}</td>
      <td className={tableau.droite}>
        {p.ecrit && !l.disparue ? (
          <Nombre
            libelle={`Part de ${l.reference}`}
            valeur={l.pourcentage}
            onChange={(v) => p.onPart(l.matiere_id, v)}
            min={0}
            max={100}
            decimales={2}
            unite="%"
          />
        ) : (
          `${nombre(l.pourcentage, 2)} %`
        )}
      </td>
      <td className={`${tableau.droite} nombre`}>{l.ml_m2 == null ? VIDE : nombre(l.ml_m2, 4)}</td>
      <td className={`${tableau.droite} nombre`} title={titreKg}>
        {lineaire && !l.densite ? <span className={styles.faux}>densité manquante</span> : nombre(l.kg_m2, 4)}
      </td>
      {p.voitPrix ? (
        <td className={`${tableau.droite} nombre`}>
          {l.prix && l.devise ? prixUnite(l.prix, l.devise, l.unite_prix ?? 'kg') : VIDE}
        </td>
      ) : null}
      {p.voitPrix ? (
        <td className={`${tableau.droite} nombre`}>{l.cout_m2 == null ? VIDE : prix(l.cout_m2)}</td>
      ) : null}
      <td>{(p.autres.get(l.matiere_id) ?? []).join(', ') || VIDE}</td>
      {p.ecrit ? (
        <td>
          <Bouton
            taille="petit"
            variante="fantome"
            titre="Retirer cette matière de la recette"
            onClick={() => p.onRetirer(l.matiere_id)}
          >
            Retirer
          </Bouton>
        </td>
      ) : null}
    </tr>
  )
}

function Groupe({ g, p, colonnes }: { g: GroupeRole; p: TableRecetteProps; colonnes: number }) {
  const faux = g.etat === 'trop' || g.etat === 'manque' || g.etat === 'vide'
  const unite = g.lineaire ? 'ml/m²' : 'kg/m²'
  return (
    <>
      <tr className={styles.groupeRole}>
        <td colSpan={colonnes}>
          <span className={faux ? styles.faux : undefined}>
            {g.role} · {nombre(g.poids, 4)} {unite}
          </span>{' '}
          <span className={g.etat === 'complet' ? styles.juste : styles.faux}>— {etatLisible(g)}</span>
        </td>
      </tr>
      {g.lignes.map((l) => (
        <Ligne key={`${l.matiere_id}-${l.reference}`} l={l} p={p} lineaire={g.lineaire} />
      ))}
    </>
  )
}

export function TableRecette(p: TableRecetteProps) {
  const titres = [
    'Référence',
    'Fournisseur',
    'Part du rôle (%)',
    'ml / m²',
    'kg / m²',
    ...(p.voitPrix ? ['Prix d’achat', 'Coût / m² (MAD)'] : []),
    'Sert aussi à',
    ...(p.ecrit ? [''] : []),
  ]
  const kg = p.groupes.reduce((s, g) => s + g.kg_m2, 0)
  const couts = p.groupes.map((g) => g.cout_m2)
  const cout = couts.every((c) => c != null) ? couts.reduce<number>((s, c) => s + (c ?? 0), 0) : null
  return (
    <Cadre hauteur="fenetre">
      <table className={tableau.table} aria-label="Recette">
        <thead>
          <tr>
            {titres.map((t, i) => (
              <th key={`${t}-${i}`} scope="col">
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {p.groupes.map((g) => (
            <Groupe key={g.role_id} g={g} p={p} colonnes={titres.length} />
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4}>Toute la recette</td>
            <td className={`${tableau.droite} nombre`}>{nombre(kg, 4)}</td>
            {p.voitPrix ? <td /> : null}
            {p.voitPrix ? (
              <td className={`${tableau.droite} nombre`}>{cout == null ? VIDE : prix(cout)}</td>
            ) : null}
            <td colSpan={p.ecrit ? 2 : 1} />
          </tr>
        </tfoot>
      </table>
    </Cadre>
  )
}
