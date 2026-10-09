/**
 * Les colonnes de la vue « Recette d'une qualité » (ECRANS-PRO 5.18) et son pied **par rôle** :
 * combien de fils de chaque rôle ont été importés, le poids du rôle au m², ce qu'on sait de son
 * coût, puis la dernière ligne « Coût matière de la qualité ».
 */
import type { Colonne } from '../../../composants/tableaux/colonnes'
import { nombre, part, pourcent, VIDE } from '../../../lib/format'
import type { Schema } from '../../../lib/types'
import { colonnesChiffres, type Groupe } from './colonnes'
import { Dossiers, LienMatiere, type Liens } from './liens'
import styles from './revient.module.css'

export type CoutQualite = Schema<'CoutQualite'>
type RoleQualite = Schema<'RoleQualite'>

/** Référence · Rôle · Part du rôle · kg / m² · Lots · chiffres · Coût / m² · Dossiers. */
export function colonnesQualite(liens: Liens): Colonne<Groupe>[] {
  const chiffres = colonnesChiffres<Groupe>((g) => g.marchandise_kg).filter(
    (c) => c.cle !== 'tva_mad' && c.cle !== 'decaisse_mad',
  )
  return [
    { cle: 'valeur', titre: 'Référence', rendu: (g) => <LienMatiere reference={g.valeur} liens={liens} /> },
    { cle: 'role', titre: 'Rôle', rendu: (g) => g.role || VIDE },
    {
      cle: 'part_recette',
      titre: 'Part du rôle',
      aide: 'La part de ce fil dans son rôle : les parts d’un rôle font 100 %',
      droite: true,
      rendu: (g) => pourcent(g.part_recette ?? 0, 1),
    },
    {
      cle: 'poids_m2',
      titre: 'kg / m²',
      aide: 'Poids du rôle au m² × part du fil',
      droite: true,
      rendu: (g) => nombre(g.poids_m2 ?? 0, 4),
    },
    { cle: 'lignes', titre: 'Lots', droite: true, rendu: (g) => nombre(g.lignes) },
    ...chiffres,
    {
      cle: 'cout_m2',
      titre: 'Coût / m²',
      aide: 'kg au m² (un cuir, des franges, un ruban : leurs ml/m² × la densité) × coût hors TVA au kilo',
      droite: true,
      rendu: (g) => <strong>{nombre(g.cout_m2 ?? 0, 2)}</strong>,
    },
    {
      cle: 'dossiers',
      titre: 'Dossiers',
      triable: false,
      valeur: (g) => g.dossiers.join(' '),
      rendu: (g) => <Dossiers numeros={g.dossiers} liens={liens} />,
    },
  ]
}

/** Ce qu'on sait du coût d'un rôle. */
export function etatDuRole(b: RoleQualite): string {
  const connu = !b.connu_m2
    ? 'aucun fil importé : rôle hors du coût calculé'
    : b.connu_m2 < b.poids_m2 - 1e-9
      ? `coût connu sur ${part(b.poids_m2 ? b.connu_m2 / b.poids_m2 : 0, 0)} du rôle, étendu au reste`
      : 'coût connu pour tout le rôle'
  return b.lineaire ? `${connu} · rôle au mètre (ml/m²), hors du poids au m²` : connu
}

/** Le coût au m² d'un rôle, étendu du connu à tout le rôle. */
export const coutDuRole = (b: RoleQualite) => (b.connu_m2 ? (b.cout_m2 / b.connu_m2) * b.poids_m2 : 0)

/** Le pied par rôle, puis « Coût matière de la qualité » (12 colonnes). */
export function PiedQualite({ r }: { r: CoutQualite }) {
  return (
    <>
      {r.roles.map((b) => (
        <tr key={b.role}>
          <td>Rôle {b.role || VIDE}</td>
          <td colSpan={2} className={styles.note}>
            {nombre(b.importes)} fil(s) importé(s) sur {nombre(b.fils)}
          </td>
          <td className={styles.droite}>{nombre(b.poids_m2, 4)}</td>
          <td colSpan={6} className={styles.note}>
            {etatDuRole(b)}
          </td>
          <td className={styles.droite}>
            <strong>{nombre(coutDuRole(b), 2)}</strong>
          </td>
          <td />
        </tr>
      ))}
      <tr>
        <td colSpan={3}>Coût matière de la qualité</td>
        <td className={styles.droite}>{nombre(r.poids_m2, 4)}</td>
        <td colSpan={6} />
        <td className={styles.droite}>
          <strong>{nombre(r.cout_m2_estime, 2)}</strong>
        </td>
        <td />
      </tr>
    </>
  )
}
