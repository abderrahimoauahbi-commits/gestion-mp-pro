/**
 * Le fil d'Ariane de la barre du haut, dérivé du registre (`routes.ts`) : groupe du menu, liste
 * parente (pour une fiche en fenêtre), écran. Aucune page n'a à le poser.
 */
import { Link } from 'react-router'

import { ecranParChemin, type Ecran } from '../../routes'
import { Icone } from '../mise-en-page/Icone'
import styles from './FilAriane.module.css'

/** Les étapes du fil pour un écran : groupe, parent (lien), écran. */
export function etapesDuFil(ecran: Ecran): { libelle: string; vers?: string }[] {
  const parent = ecran.parent ? ecranParChemin(ecran.parent) : undefined
  const groupe = (parent ?? ecran).groupe
  const etapes: { libelle: string; vers?: string }[] = []
  if (groupe) etapes.push({ libelle: groupe })
  if (parent) etapes.push({ libelle: parent.titre, vers: parent.chemin })
  etapes.push({ libelle: ecran.titre })
  return etapes
}

export function FilAriane({ ecran }: { ecran: Ecran | null }) {
  if (!ecran) return null
  const etapes = etapesDuFil(ecran)
  return (
    <nav aria-label="Fil d’Ariane" className={styles.fil}>
      <ol>
        {etapes.map((e, i) => {
          const dernier = i === etapes.length - 1
          return (
            <li key={`${e.libelle}-${i}`} aria-current={dernier ? 'page' : undefined}>
              {e.vers ? <Link to={e.vers}>{e.libelle}</Link> : <span>{e.libelle}</span>}
              {dernier ? null : <Icone nom="chevron" taille={12} />}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
