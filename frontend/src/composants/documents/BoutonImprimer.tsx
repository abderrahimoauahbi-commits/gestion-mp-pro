/**
 * Imprimer un document du serveur (bon fournisseur, étiquettes, bilan, feuille d'inventaire) :
 * il s'ouvre **dans un nouvel onglet** — la fiche d'où l'on vient reste ouverte (REC-achats M9 :
 * Gestion MP imprimait dans le même onglet, et « Retour » ne rouvrait pas la fenêtre).
 * `taille="atelier"` : toute la largeur, 46 px de haut (cible tactile du téléphone).
 */
import { adresseApi } from '../../lib/api'
import { classes } from '../mise-en-page/classes'
import { Icone } from '../mise-en-page/Icone'
import styles from './BoutonImprimer.module.css'

type Parametre = string | number | boolean | null | undefined

export function BoutonImprimer({
  route,
  parametres,
  libelle = 'Imprimer',
  titre,
  taille = 'normal',
}: {
  route: string
  parametres?: Record<string, Parametre | Parametre[]>
  libelle?: string
  titre?: string
  taille?: 'normal' | 'atelier'
}) {
  return (
    <a
      className={classes(styles.imprimer, taille === 'atelier' && styles.atelier)}
      href={adresseApi(route, parametres)}
      target="_blank"
      rel="noopener"
      title={titre ?? 'S’ouvre dans un nouvel onglet, prêt à imprimer (A4)'}
    >
      <Icone nom="imprimer" />
      {libelle}
    </a>
  )
}
