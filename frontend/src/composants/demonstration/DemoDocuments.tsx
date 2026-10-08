/** Démonstration des documents : pièces jointes, historique, liens par numéro, impression. */
import { BoutonImprimer } from '../documents/BoutonImprimer'
import { Historique } from '../documents/Historique'
import { LienDocument } from '../documents/LienDocument'
import { PiecesJointes } from '../documents/PiecesJointes'
import { Carte } from '../mise-en-page/Carte'
import { Page } from '../mise-en-page/Page'
import styles from './Demonstration.module.css'

export function DemoDocuments() {
  return (
    <Page titre="Documents">
      <Carte titre="Liens et impression">
        <div className={styles.rangee}>
          <LienDocument genre="commande" id={12} numero="BC-2026-0012" />
          <LienDocument genre="reception" id={4} numero={null} />
          <LienDocument genre="commande" id={7} numero={null} statut="a_approuver" />
          <BoutonImprimer route="/documents/commandes/12/bon" libelle="Imprimer le bon" />
        </div>
      </Carte>
      <div className={styles.colonnes}>
        <Carte titre="Pièces jointes">
          <PiecesJointes objet="commande" id={12} />
        </Carte>
        <Carte titre="Historique">
          <Historique objet="commande" id={12} />
        </Carte>
      </div>
    </Page>
  )
}
