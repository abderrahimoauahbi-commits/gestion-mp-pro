/** Une petite courbe dans une cellule ou un indicateur : la tendance, dite aussi en texte (« de 12 à 18 »). */
import { nombre } from '../../lib/format'
import { couleurDeSerie } from '../../lib/teintes'
import { morceaux } from './Courbes'
import { bornes } from './echelle'
import styles from './Graphique.module.css'

export function Sparkline({
  valeurs,
  libelle,
  couleur = couleurDeSerie(0),
  largeur = 80,
  hauteur = 22,
}: {
  valeurs: readonly (number | null)[]
  libelle: string
  couleur?: string
  largeur?: number
  hauteur?: number
}) {
  const [min, max] = bornes([{ nom: libelle, valeurs }])
  const pleines = valeurs.filter((v): v is number => v != null)
  const premier = pleines[0]
  const dernier = pleines[pleines.length - 1]
  const dit =
    premier == null || dernier == null
      ? `${libelle} : pas de données`
      : `${libelle} : de ${nombre(premier, 0, 2)} à ${nombre(dernier, 0, 2)}`
  const x = (i: number) => 1 + ((largeur - 2) * i) / Math.max(1, valeurs.length - 1)
  const y = (v: number) => 1 + (hauteur - 2) * (1 - (v - min) / (max - min || 1))
  const traits = morceaux(valeurs.map((v, i) => (v == null ? null : ([x(i), y(v)] as const))))
  return (
    <svg
      className={styles.sparkline}
      width={largeur}
      height={hauteur}
      viewBox={`0 0 ${largeur} ${hauteur}`}
      role="img"
      aria-label={dit}
    >
      {traits.map((t) => (
        <polyline
          key={t}
          points={t}
          fill="none"
          strokeWidth="1.6"
          strokeLinejoin="round"
          style={{ stroke: couleur }}
        />
      ))}
    </svg>
  )
}
