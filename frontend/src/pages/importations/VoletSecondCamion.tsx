/**
 * Fiche dossier › Second camion d'une facture du dossier (ECRANS-PRO 5.12) : la marchandise reçue
 * depuis par une de ses factures (`a_rattacher` de la fiche, fournisseurs marocains compris,
 * anomalie 5.10) rejoint ce dossier, toute sa marchandise libre d'un coup (on rattache par
 * facture, jamais ligne à ligne : une ligne reçue ne sort qu'avec toute sa réception).
 */
import { dire } from '../../composants/retour/Messages'
import { Note } from '../../composants/retour/Note'
import { kg, nombre } from '../../lib/format'
import { ChoixFacture } from './ChoixFacture'
import styles from './Importations.module.css'
import type { DossierFiche } from './types'
import { direLesAvis, type GestesDossier } from './useDossier'

export function VoletSecondCamion({ d, g }: { d: DossierFiche; g: GestesDossier }) {
  const f = d.a_rattacher.length === 1 ? d.a_rattacher[0] : undefined
  const note = f
    ? `La facture ${f.numero} est arrivée en plus d’un camion : ce qui est reçu depuis rejoint son dossier.`
    : 'Des factures de ce dossier sont arrivées en plus d’un camion : ce qui est reçu depuis rejoint ce dossier.'
  return (
    <div className={styles.pile}>
      <Note>{note}</Note>
      <ChoixFacture
        factures={d.a_rattacher}
        hauteur="fenetre"
        action={() => 'Ajouter au dossier'}
        blocages={() => (d.actions.rattacher ? [d.actions.rattacher] : [])}
        onChoisir={async (f) => {
          const relu = await g.rattacher(f.facture_id)
          dire(
            `Second camion de la facture ${f.numero} ajouté : ${nombre(f.lots)} lot(s), ${kg(f.quantite)}.`,
          )
          direLesAvis(relu)
        }}
      />
    </div>
  )
}
