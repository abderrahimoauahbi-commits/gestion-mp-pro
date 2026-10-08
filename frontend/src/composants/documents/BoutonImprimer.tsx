/**
 * Imprimer un document du serveur (bon fournisseur, étiquettes, bilan, feuille d'inventaire) :
 * il s'ouvre **dans un nouvel onglet** — la fiche d'où l'on vient reste ouverte (REC-achats M9 :
 * Gestion MP imprimait dans le même onglet, et « Retour » ne rouvrait pas la fenêtre).
 */
import { adresseApi } from '../../lib/api'
import { Icone } from '../mise-en-page/Icone'
import styles from './BoutonImprimer.module.css'

type Parametre = string | number | boolean | null | undefined

export function BoutonImprimer({
  route,
  parametres,
  libelle = 'Imprimer',
  titre,
}: {
  route: string
  parametres?: Record<string, Parametre | Parametre[]>
  libelle?: string
  titre?: string
}) {
  return (
    <a
      className={styles.imprimer}
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
