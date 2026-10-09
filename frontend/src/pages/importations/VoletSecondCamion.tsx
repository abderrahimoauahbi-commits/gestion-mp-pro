/**
 * Fiche dossier › Second camion de la facture (ECRANS-PRO 5.12) : la marchandise reçue depuis par la
 * même facture (`a_rattacher` de la fiche, fournisseurs marocains compris, anomalie 5.10) rejoint ce
 * dossier, toute sa marchandise libre d'un coup (un dossier = une facture = une livraison : on
 * rattache par facture, jamais ligne à ligne).
 */
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { kg, nombre } from '../../lib/format'
import { ChoixFacture } from './ChoixFacture'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'
import type { GestesDossier } from './useDossier'

export function VoletSecondCamion({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  const note = d.facture
    ? `La facture ${d.facture.numero} est arrivée en plus d’un camion : ce qui est reçu depuis rejoint son dossier.`
    : 'Les factures de ce dossier sont arrivées en plus d’un camion : ce qui est reçu depuis rejoint ce dossier.'
  return (
    <div className={styles.pile}>
      <Note>{note}</Note>
      <ChoixFacture
        factures={d.a_rattacher}
        hauteur="fenetre"
        action={() => 'Ajouter au dossier'}
        blocages={() => (d.actions.rattacher ? [d.actions.rattacher] : [])}
        onChoisir={async (f) => {
          await g.rattacher(f.facture_id)
          dire(
            `Second camion de la facture ${f.numero} ajouté : ${nombre(f.lots)} lot(s), ${kg(f.quantite)}.`,
          )
        }}
      />
    </div>
  )
}
