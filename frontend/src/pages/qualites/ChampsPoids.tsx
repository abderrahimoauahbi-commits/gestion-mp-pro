/**
 * Les poids d'un m² de tapis, rôle par rôle : kg/m², ou **ml/m²** pour un rôle au mètre (cuir,
 * franges, ruban : les kg/m² s'en calculent par la densité de la matière). Un rôle à zéro n'entre
 * pas dans la qualité (les poids nuls ne s'enregistrent pas, P7-5).
 */
import { Grille } from '../../composants/mise-en-page/Grille'
import { Champ } from '../../composants/saisie/Champ'
import { Nombre } from '../../composants/saisie/Nombre'
import type { RoleQualite } from './recette'

/** Le plus grand poids au m² accepté par le serveur (`POIDS_MAXI`). */
export const POIDS_MAX = 1_000_000

export function ChampsPoids({
  roles,
  poids,
  onChange,
  lecture,
  compact,
}: {
  roles: readonly RoleQualite[]
  poids: Readonly<Record<number, number | null>>
  onChange: (role_id: number, v: number | null) => void
  lecture?: boolean
  /** Sans l'aide sous chaque champ (l'unité dit déjà ml/m² ou kg/m²) : la recette garde la place. */
  compact?: boolean
}) {
  return (
    <Grille colonnes={4}>
      {roles.map((r) => (
        <Champ
          key={r.role_id}
          libelle={r.role}
          aide={
            compact ? undefined : r.lineaire ? 'mètres linéaires par m² de tapis' : 'kilos par m² de tapis'
          }
        >
          <Nombre
            valeur={poids[r.role_id] ?? null}
            onChange={(v) => onChange(r.role_id, v)}
            min={0}
            max={POIDS_MAX}
            decimales={4}
            unite={r.lineaire ? 'ml / m²' : 'kg / m²'}
            desactive={lecture}
          />
        </Champ>
      ))}
    </Grille>
  )
}

/** Les rôles de la classification, dans leur ordre (celui des listes et des colonnes). */
export function rolesDansLOrdre(
  roles: readonly { id: number; code: string; lineaire: boolean; ordre: number }[],
): RoleQualite[] {
  return [...roles]
    .sort((a, b) => a.ordre - b.ordre || a.code.localeCompare(b.code))
    .map((r) => ({ role_id: r.id, role: r.code, lineaire: r.lineaire }))
}
